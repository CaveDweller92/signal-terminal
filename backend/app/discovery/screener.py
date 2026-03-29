"""
Pre-market Screener — scans the universe and surfaces the top 30 stocks.

Runs daily at 5:00 AM ET. Scores each stock on 6 dimensions:
  1. Volume score     — relative volume vs 20-day average
  2. Gap score        — pre-market gap percentage
  3. Technical score  — RSI, EMA trend, MACD alignment
  4. Fundamental score — 20-day price momentum + Sharpe-like ratio (from daily data)
  5. News score       — Finnhub article count/recency (last 3 days)
  6. Sector score     — SPDR sector ETF (US) or iShares TSX sector ETF (CA)
                        5-day return relative to SPY / XIU.TO

Composite = weighted sum of all 6 scores.
Top 30 by composite score are saved to screener_results.

Rate limiting: Massive API is capped at 100 calls/min. The screener processes
stocks in batches (BATCH_SIZE) with a cooldown between batches so total API
call rate stays at or below MASSIVE_MAX_CALLS_PER_MIN.
"""

import asyncio
import logging
from datetime import date, timedelta

import httpx
import numpy as np
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.engine.data_provider import DataProvider
from app.engine.indicators import calc_rsi, calc_ema, calc_macd, calc_volume_ratio
from app.models.screener_result import ScreenerResult
from app.models.stock_universe import StockUniverse

logger = logging.getLogger(__name__)

# SPDR sector ETF tickers — benchmark: SPY
SECTOR_ETF_MAP_US: dict[str, str] = {
    "Technology": "XLK",
    "Financial Services": "XLF",
    "Healthcare": "XLV",
    "Consumer Cyclical": "XLY",
    "Consumer Defensive": "XLP",
    "Energy": "XLE",
    "Industrials": "XLI",
    "Materials": "XLB",
    "Real Estate": "XLRE",
    "Utilities": "XLU",
    "Communication Services": "XLC",
}

# iShares S&P/TSX sector ETFs — benchmark: XIU.TO
# Sectors without a liquid TSX-specific ETF are omitted; those stocks fall back to 5.0.
SECTOR_ETF_MAP_CA: dict[str, str] = {
    "Financial Services": "XFN.TO",
    "Energy":             "XEG.TO",
    "Materials":          "XMA.TO",
    "Technology":         "XIT.TO",
    "Real Estate":        "XRE.TO",
    "Utilities":          "XUT.TO",
    "Consumer Defensive": "XST.TO",
    "Industrials":        "ZIN.TO",
}


class PremarketScreener:
    # Weights for composite score (sum = 1.0)
    WEIGHTS = {
        "volume": 0.20,
        "gap": 0.15,
        "technical": 0.30,
        "fundamental": 0.10,
        "news": 0.10,
        "sector": 0.15,
    }

    # Rate limiting: each stock = 2 Massive API calls (intraday + daily).
    # Keep total rate at or below MASSIVE_MAX_CALLS_PER_MIN.
    BATCH_SIZE = 10
    MASSIVE_CALLS_PER_STOCK = 2
    MASSIVE_MAX_CALLS_PER_MIN = 80  # stay below the 100/min hard limit

    # seconds to wait after each batch so we don't exceed the rate cap
    # BATCH_SIZE * CALLS_PER_STOCK calls per batch, spread over BATCH_DELAY_SECS
    BATCH_DELAY_SECS: float = (
        BATCH_SIZE * MASSIVE_CALLS_PER_STOCK / MASSIVE_MAX_CALLS_PER_MIN * 60
    )  # = 10 * 2 / 80 * 60 = 15 s

    def __init__(self, data_provider: DataProvider):
        self.data = data_provider

    async def scan(
        self,
        stocks: list[StockUniverse],
        db: AsyncSession,
        top_n: int = 30,
    ) -> list[ScreenerResult]:
        """
        Scan all stocks, score them, save ALL scored results to DB.
        Results are flushed after each batch so partial data is available
        if the scan is interrupted.
        Returns the top_n ScreenerResult objects by composite score.
        """
        today = date.today()

        # Clear today's existing results (idempotent)
        await db.execute(
            delete(ScreenerResult).where(ScreenerResult.scan_date == today)
        )

        # Pre-fetch sector ETF performance once (~12 API calls) before main loop
        logger.info("Fetching sector ETF performance…")
        sector_perf = await self._fetch_sector_performance()
        logger.info(
            "Sector ETF data ready — US: %d sectors, CA: %d sectors",
            len(sector_perf.get("us", {})),
            len(sector_perf.get("ca", {})),
        )

        scored: list[dict] = []
        saved_rows: dict[str, ScreenerResult] = {}  # symbol → row, for return value
        total = len(stocks)

        for batch_start in range(0, total, self.BATCH_SIZE):
            batch = stocks[batch_start : batch_start + self.BATCH_SIZE]
            t0 = asyncio.get_event_loop().time()

            # Score all stocks in this batch concurrently
            tasks = [self._score_stock(stock, sector_perf) for stock in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            batch_results: list[ScreenerResult] = []
            for stock, result in zip(batch, results):
                if isinstance(result, Exception):
                    logger.debug("Skipping %s: %s", stock.symbol, result)
                    continue
                result["symbol"] = stock.symbol
                result["exchange"] = stock.exchange
                result["sector_name"] = stock.sector
                scored.append(result)

                row = ScreenerResult(
                    scan_date=today,
                    symbol=result["symbol"],
                    exchange=result["exchange"],
                    composite_score=round(result["composite"], 4),
                    volume_score=round(result["volume"], 4),
                    gap_score=round(result["gap"], 4),
                    technical_score=round(result["technical"], 4),
                    fundamental_score=round(result["fundamental"], 4),
                    news_score=round(result["news"], 4),
                    sector_score=round(result["sector"], 4),
                    premarket_gap_pct=round(result.get("gap_pct", 0), 4),
                    relative_volume=round(result.get("rel_volume", 1), 2),
                    sector=result["sector_name"],
                    has_catalyst=result.get("has_catalyst", False),
                )
                db.add(row)
                saved_rows[result["symbol"]] = row
                batch_results.append(row)

            # Flush after each batch — results available in DB even if scan is interrupted
            await db.flush()

            processed = min(batch_start + self.BATCH_SIZE, total)
            print(f"  {processed}/{total} scored ({len(scored)} with data)…", flush=True)

            # Rate-limit cooldown — wait out remaining slice time between batches
            if batch_start + self.BATCH_SIZE < total:
                elapsed = asyncio.get_event_loop().time() - t0
                wait = max(0.0, self.BATCH_DELAY_SECS - elapsed)
                if wait > 0:
                    await asyncio.sleep(wait)

        await db.commit()
        logger.info("Screener complete: %d stocks scored and saved", len(scored))

        # Return top N for callers that need an immediate ranked list
        scored.sort(key=lambda s: s["composite"], reverse=True)
        return [saved_rows[e["symbol"]] for e in scored[:top_n] if e["symbol"] in saved_rows]

    async def _score_stock(self, stock: StockUniverse, sector_perf: dict[str, float]) -> dict:
        """Score a single stock on all 6 dimensions (0-10 scale each)."""
        bars = await self.data.get_intraday(stock.symbol)
        daily = await self.data.get_daily(stock.symbol)

        if not bars or not daily:
            raise ValueError(f"No data for {stock.symbol}")

        closes = np.array([b["close"] for b in bars])
        volumes = np.array([b["volume"] for b in bars], dtype=float)
        daily_closes = np.array([b["close"] for b in daily])

        # 1. Volume score — relative volume spike
        vol_ratio = calc_volume_ratio(volumes)
        current_vol = float(vol_ratio[-1]) if len(vol_ratio) > 0 and not np.isnan(vol_ratio[-1]) else 1.0
        volume_score = min(10.0, current_vol * 3)  # 3x avg = score 9

        # 2. Gap score — pre-market gap vs prior close
        if len(daily_closes) >= 2:
            gap_pct = ((closes[0] - daily_closes[-2]) / daily_closes[-2]) * 100
        else:
            gap_pct = 0.0
        gap_score = min(10.0, abs(gap_pct) * 2)  # 5% gap = score 10

        # 3. Technical score — RSI + EMA trend + MACD alignment
        rsi = calc_rsi(daily_closes)
        current_rsi = float(rsi[-1]) if len(rsi) > 0 and not np.isnan(rsi[-1]) else 50.0

        ema_fast = calc_ema(daily_closes, 9)
        ema_slow = calc_ema(daily_closes, 21)
        ema_bullish = (
            len(ema_fast) > 0
            and len(ema_slow) > 0
            and not np.isnan(ema_fast[-1])
            and not np.isnan(ema_slow[-1])
            and ema_fast[-1] > ema_slow[-1]
        )

        _, _, histogram = calc_macd(daily_closes)
        macd_bull = len(histogram) > 0 and not np.isnan(histogram[-1]) and histogram[-1] > 0

        tech_score = 5.0
        if current_rsi < 35:
            tech_score += 2.5  # oversold bounce opportunity
        elif current_rsi > 65:
            tech_score += 1.0  # momentum
        if ema_bullish:
            tech_score += 1.5
        if macd_bull:
            tech_score += 1.0
        tech_score = min(10.0, tech_score)

        # 4. Fundamental score — 20-day price momentum + return/risk (Sharpe proxy)
        fundamental_score = self._calc_fundamental_score(daily_closes)

        # 5. News score — Finnhub article count (last 3 days)
        news_score, has_catalyst = await self._fetch_news_score(stock.symbol)

        # 6. Sector score — sector ETF performance relative to market benchmark
        sector_score = self._calc_sector_score(stock.sector, stock.exchange, sector_perf)

        # Composite
        composite = (
            volume_score * self.WEIGHTS["volume"]
            + gap_score * self.WEIGHTS["gap"]
            + tech_score * self.WEIGHTS["technical"]
            + fundamental_score * self.WEIGHTS["fundamental"]
            + news_score * self.WEIGHTS["news"]
            + sector_score * self.WEIGHTS["sector"]
        )

        return {
            "volume": volume_score,
            "gap": gap_score,
            "technical": tech_score,
            "fundamental": fundamental_score,
            "news": news_score,
            "sector": sector_score,
            "composite": composite,
            "gap_pct": gap_pct,
            "rel_volume": current_vol,
            "has_catalyst": has_catalyst,
        }

    # ------------------------------------------------------------------ #
    # Score helpers                                                        #
    # ------------------------------------------------------------------ #

    def _calc_fundamental_score(self, daily_closes: np.ndarray) -> float:
        """
        Price-based fundamental proxy using 20-day momentum and Sharpe-like ratio.
        Uses data already fetched — no extra API calls.
        """
        if len(daily_closes) < 5:
            return 5.0

        score = 3.0  # base

        # 20-day momentum
        lookback = min(20, len(daily_closes) - 1)
        momentum_pct = (daily_closes[-1] - daily_closes[-lookback - 1]) / daily_closes[-lookback - 1] * 100
        if momentum_pct > 10:
            score += 4.0
        elif momentum_pct > 5:
            score += 3.0
        elif momentum_pct > 0:
            score += 2.0
        elif momentum_pct > -5:
            score += 1.0
        # negative momentum below -5%: no bonus

        # Return/risk ratio (Sharpe proxy, annualised not needed — just relative)
        returns = np.diff(daily_closes) / daily_closes[:-1]
        if len(returns) >= 5:
            mean_r = float(np.mean(returns))
            std_r = float(np.std(returns))
            if std_r > 0:
                sharpe = mean_r / std_r
                if sharpe > 1.0:
                    score += 3.0
                elif sharpe > 0.5:
                    score += 2.0
                elif sharpe > 0:
                    score += 1.0

        return min(10.0, score)

    async def _fetch_news_score(self, symbol: str) -> tuple[float, bool]:
        """
        Fetch recent Finnhub news article count as a catalyst proxy.
        Returns (score 0-10, has_catalyst).
        Falls back to neutral (5.0, False) if Finnhub key not set or request fails.
        """
        if not settings.finnhub_api_key:
            return 5.0, False

        today = date.today()
        from_date = (today - timedelta(days=3)).isoformat()
        to_date = today.isoformat()
        url = (
            f"https://finnhub.io/api/v1/company-news"
            f"?symbol={symbol}&from={from_date}&to={to_date}"
            f"&token={settings.finnhub_api_key}"
        )

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url)
            if resp.status_code != 200:
                return 5.0, False
            articles = resp.json()
            count = len(articles) if isinstance(articles, list) else 0
        except Exception:
            return 5.0, False

        has_catalyst = count >= 3

        # Map article count to 0-10 score
        if count == 0:
            score = 3.0
        elif count <= 2:
            score = 5.0
        elif count <= 5:
            score = 7.0
        else:
            score = min(10.0, 7.0 + (count - 5) * 0.3)

        return score, has_catalyst

    async def _fetch_sector_performance(self) -> dict[str, dict[str, float]]:
        """
        Fetch 5-day sector ETF returns relative to their market benchmark.

        US stocks: SPDR ETFs vs SPY   (~12 Massive calls)
        CA stocks: iShares TSX ETFs vs XIU.TO  (~9 yfinance calls)

        Returns {"us": {sector: rel_return}, "ca": {sector: rel_return}}.
        Either sub-dict may be empty if the benchmark fetch fails.
        """
        result: dict[str, dict[str, float]] = {"us": {}, "ca": {}}

        # --- US sector ETFs vs SPY ---
        try:
            spy_daily = await self.data.get_daily("SPY")
            spy_return = self._calc_5d_return(spy_daily)
            for sector, etf in SECTOR_ETF_MAP_US.items():
                try:
                    etf_daily = await self.data.get_daily(etf)
                    result["us"][sector] = self._calc_5d_return(etf_daily) - spy_return
                except Exception as e:
                    logger.debug("US sector ETF %s failed: %s", etf, e)
                    result["us"][sector] = 0.0
        except Exception as e:
            logger.warning("Could not fetch SPY — US sector scores will be neutral: %s", e)

        # --- Canadian sector ETFs vs XIU.TO ---
        try:
            xiu_daily = await self.data.get_daily("XIU.TO")
            xiu_return = self._calc_5d_return(xiu_daily)
            for sector, etf in SECTOR_ETF_MAP_CA.items():
                try:
                    etf_daily = await self.data.get_daily(etf)
                    result["ca"][sector] = self._calc_5d_return(etf_daily) - xiu_return
                except Exception as e:
                    logger.debug("CA sector ETF %s failed: %s", etf, e)
                    result["ca"][sector] = 0.0
        except Exception as e:
            logger.warning("Could not fetch XIU.TO — CA sector scores will be neutral: %s", e)

        return result

    @staticmethod
    def _calc_5d_return(daily: list[dict]) -> float:
        """5-day price return in percent."""
        if len(daily) < 6:
            return 0.0
        closes = [b["close"] for b in daily]
        return (closes[-1] - closes[-6]) / closes[-6] * 100

    def _calc_sector_score(
        self,
        sector: str | None,
        exchange: str | None,
        sector_perf: dict[str, dict[str, float]],
    ) -> float:
        """
        Map sector relative return to a 0-10 score.
        +5% vs benchmark → 10, −5% → 0, neutral (0%) → 5.

        TSX stocks use Canadian sector ETFs (XIU.TO benchmark).
        All others use US SPDR ETFs (SPY benchmark).
        """
        is_tsx = (exchange or "").upper() in ("TSX", "TSX-V") or (sector or "").endswith(".TO")
        perf_map = sector_perf.get("ca" if is_tsx else "us", {})

        if not perf_map:
            return 5.0

        rel_return = perf_map.get(sector or "", 0.0)
        score = 5.0 + rel_return
        return min(10.0, max(0.0, score))
