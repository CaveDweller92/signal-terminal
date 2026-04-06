"""
Pre-market Screener — scans the universe and surfaces the top 30 stocks.

Runs daily at 5:00 AM ET. Scores each stock on 6 dimensions:
  1. Volume score     — relative volume vs 20-day average
  2. Gap score        — pre-market gap percentage
  3. Technical score  — RSI, EMA trend, MACD alignment
  4. Fundamental score — stock quality (Sharpe ratio, max drawdown, price stability)
  5. News score       — Massive news for US / Finnhub for .TO (last 3 days)
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
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.engine.data_provider import DataProvider
from app.engine.indicators import (
    calc_adx,
    calc_bollinger_bands,
    calc_ema,
    calc_macd,
    calc_rsi,
    calc_stochastic,
    calc_volume_ratio,
    detect_divergence,
)
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
    # Weights for composite score (sum = 1.0) — swing trading
    WEIGHTS = {
        "volume": 0.10,
        "momentum": 0.20,  # replaces gap score (multi-day momentum)
        "technical": 0.30,
        "fundamental": 0.10,
        "news": 0.10,
        "sector": 0.20,
    }

    # Massive (US news) is unlimited. Finnhub (only .TO news) has 60 calls/min
    # but TSX stocks are a small fraction of the universe.
    BATCH_SIZE = 50
    BATCH_DELAY_SECS: float = 2.0

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

        # Pre-fetch sector ETF performance once (~12 API calls) before main loop
        logger.info("Fetching sector ETF performance…")
        sector_perf = await self._fetch_sector_performance()
        logger.info(
            "Sector ETF data ready — US: %d sectors, CA: %d sectors",
            len(sector_perf.get("us", {})),
            len(sector_perf.get("ca", {})),
        )

        scored: list[dict] = []
        failed: list[str] = []
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
                    failed.append(stock.symbol)
                    continue
                result["symbol"] = stock.symbol
                result["exchange"] = stock.exchange
                result["sector_name"] = stock.sector
                scored.append(result)

                row_data = dict(
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
                # Upsert — safe for concurrent/rerun scans
                stmt = pg_insert(ScreenerResult).values(**row_data)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["scan_date", "symbol"],
                    set_={k: stmt.excluded[k] for k in row_data if k not in ("scan_date", "symbol")},
                ).returning(ScreenerResult)
                upsert_result = await db.execute(stmt)
                row = upsert_result.scalar_one()
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
        if failed:
            logger.warning("Screener: %d symbols failed: %s", len(failed), ", ".join(failed))
        logger.info("Screener complete: %d stocks scored and saved", len(scored))

        # Return top N for callers that need an immediate ranked list
        scored.sort(key=lambda s: s["composite"], reverse=True)
        return [saved_rows[e["symbol"]] for e in scored[:top_n] if e["symbol"] in saved_rows]

    async def _score_stock(self, stock: StockUniverse, sector_perf: dict[str, float]) -> dict:
        """Score a single stock on 6 dimensions (0-10 scale each) using daily bars."""
        daily = await self.data.get_daily(stock.symbol)

        if not daily or len(daily) < 20:
            raise ValueError(f"Insufficient daily data for {stock.symbol}")

        daily_closes = np.array([b["close"] for b in daily])
        daily_volumes = np.array([b["volume"] for b in daily], dtype=float)

        # 1. Volume score — relative daily volume
        vol_ratio = calc_volume_ratio(daily_volumes)
        current_vol = float(vol_ratio[-1]) if len(vol_ratio) > 0 and not np.isnan(vol_ratio[-1]) else 1.0
        volume_score = min(10.0, current_vol * 3)

        # 2. Momentum score — 5-day and 20-day price momentum (replaces gap score)
        momentum_5d = 0.0
        momentum_20d = 0.0
        if len(daily_closes) >= 6:
            momentum_5d = (daily_closes[-1] - daily_closes[-6]) / daily_closes[-6] * 100
        if len(daily_closes) >= 21:
            momentum_20d = (daily_closes[-1] - daily_closes[-21]) / daily_closes[-21] * 100
        # Score: positive momentum = higher score, capped at 10
        momentum_score = 5.0 + min(2.5, max(-2.5, momentum_5d * 0.5)) + min(2.5, max(-2.5, momentum_20d * 0.25))
        momentum_score = max(0.0, min(10.0, momentum_score))

        # 3. Technical score — 7 indicators matching the analyzer (daily)
        daily_highs = np.array([b["high"] for b in daily])
        daily_lows = np.array([b["low"] for b in daily])

        rsi = calc_rsi(daily_closes)
        current_rsi = float(rsi[-1]) if len(rsi) > 0 and not np.isnan(rsi[-1]) else 50.0

        ema_fast = calc_ema(daily_closes, 10)
        ema_slow = calc_ema(daily_closes, 50)
        ema_bullish = (
            not np.isnan(ema_fast[-1]) and not np.isnan(ema_slow[-1])
            and ema_fast[-1] > ema_slow[-1]
        )

        _, _, histogram = calc_macd(daily_closes)
        macd_bull = not np.isnan(histogram[-1]) and histogram[-1] > 0

        _, _, _, bb_pct_b = calc_bollinger_bands(daily_closes)
        current_bb = float(bb_pct_b[-1]) if not np.isnan(bb_pct_b[-1]) else 0.5

        stoch_k, _ = calc_stochastic(daily_highs, daily_lows, daily_closes)
        current_stoch = float(stoch_k[-1]) if not np.isnan(stoch_k[-1]) else 50.0

        adx = calc_adx(daily_highs, daily_lows, daily_closes)
        current_adx = float(adx[-1]) if not np.isnan(adx[-1]) else 25.0

        divergence = detect_divergence(daily_closes, rsi)

        tech_score = 3.0  # base

        # RSI (0-2 pts)
        if current_rsi < 35:
            tech_score += 2.0  # oversold bounce
        elif current_rsi > 65:
            tech_score += 1.0  # momentum

        # EMA trend (0-1.5 pts)
        if ema_bullish:
            tech_score += 1.5

        # MACD (0-1 pt)
        if macd_bull:
            tech_score += 1.0

        # Bollinger Bands (0-1 pt)
        if current_bb < 0.1:
            tech_score += 1.0  # squeezed below lower band
        elif current_bb < 0.25:
            tech_score += 0.5  # near lower band

        # Stochastic (0-1 pt)
        if current_stoch < 20:
            tech_score += 1.0  # oversold
        elif current_stoch > 80:
            tech_score += 0.5  # strong momentum

        # ADX trend strength (multiplier)
        if current_adx > 30:
            tech_score *= 1.15  # trending — signals more reliable

        # Divergence (0-1 pt)
        if divergence.get("type") == "bullish" and divergence.get("confidence", 0) >= 0.3:
            tech_score += 1.0

        tech_score = min(10.0, tech_score)

        # 4. Fundamental score — stock quality (Sharpe, drawdown, stability)
        fundamental_score = self._calc_fundamental_score(daily_closes)

        # 5. News score — Finnhub article count (last 7 days)
        news_score, has_catalyst = await self._fetch_news_score(stock.symbol)

        # 6. Sector score — sector ETF performance relative to market benchmark
        sector_score = self._calc_sector_score(stock.sector, stock.exchange, sector_perf)

        # Composite
        composite = (
            volume_score * self.WEIGHTS["volume"]
            + momentum_score * self.WEIGHTS["momentum"]
            + tech_score * self.WEIGHTS["technical"]
            + fundamental_score * self.WEIGHTS["fundamental"]
            + news_score * self.WEIGHTS["news"]
            + sector_score * self.WEIGHTS["sector"]
        )

        return {
            "volume": volume_score,
            "gap": momentum_score,  # reuse DB column, now holds momentum
            "technical": tech_score,
            "fundamental": fundamental_score,
            "news": news_score,
            "sector": sector_score,
            "composite": composite,
            "gap_pct": momentum_5d,  # reuse field for 5-day momentum %
            "rel_volume": current_vol,
            "has_catalyst": has_catalyst,
        }

    # ------------------------------------------------------------------ #
    # Score helpers                                                        #
    # ------------------------------------------------------------------ #

    def _calc_fundamental_score(self, daily_closes: np.ndarray) -> float:
        """
        Stock quality score — measures consistency and risk-adjusted returns.
        Distinct from momentum (which measures direction/speed).

        Components:
          1. Sharpe-like ratio (return per unit of risk)
          2. Drawdown resilience (max drawdown over 20 days)
          3. Price stability (% of days closing above 20-day SMA)
        """
        if len(daily_closes) < 20:
            return 5.0

        score = 0.0
        recent = daily_closes[-20:]

        # 1. Sharpe-like ratio (0-4 pts)
        returns = np.diff(recent) / recent[:-1]
        mean_r = float(np.mean(returns))
        std_r = float(np.std(returns))
        if std_r > 0:
            sharpe = mean_r / std_r
            if sharpe > 1.0:
                score += 4.0
            elif sharpe > 0.5:
                score += 3.0
            elif sharpe > 0:
                score += 1.5

        # 2. Max drawdown resilience (0-3 pts) — shallow drawdown = quality
        peak = recent[0]
        max_dd = 0.0
        for p in recent:
            if p > peak:
                peak = p
            dd = (peak - p) / peak
            if dd > max_dd:
                max_dd = dd

        if max_dd < 0.03:
            score += 3.0  # <3% drawdown — very stable
        elif max_dd < 0.07:
            score += 2.0  # <7% — reasonable
        elif max_dd < 0.12:
            score += 1.0  # <12% — moderate
        # >12% drawdown: no points

        # 3. Price stability — % of days above 20-day SMA (0-3 pts)
        sma_20 = float(np.mean(recent))
        above_sma = float(np.sum(recent >= sma_20)) / len(recent)
        if above_sma >= 0.7:
            score += 3.0  # 70%+ days above SMA — strong support
        elif above_sma >= 0.5:
            score += 2.0
        elif above_sma >= 0.35:
            score += 1.0

        return min(10.0, score)

    async def _fetch_news_score(self, symbol: str) -> tuple[float, bool]:
        """
        Fetch recent news article count as a catalyst proxy.
        US stocks use Massive /v2/reference/news (unlimited).
        .TO stocks use Finnhub /company-news (low volume, within 60/min limit).
        Returns (score 0-10, has_catalyst).
        """
        is_tsx = symbol.endswith(".TO")

        if is_tsx:
            count = await self._fetch_news_count_finnhub(symbol)
        else:
            count = await self._fetch_news_count_massive(symbol)

        if count is None:
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

    async def _fetch_news_count_massive(self, symbol: str) -> int | None:
        """Fetch news count from Massive /v2/reference/news (unlimited)."""
        if not settings.massive_api_key:
            return None

        today = date.today()
        from_date = (today - timedelta(days=3)).isoformat()
        url = (
            f"https://api.massive.com/v2/reference/news"
            f"?ticker={symbol}"
            f"&published_utc.gte={from_date}"
            f"&limit=20&sort=published_utc&order=desc"
            f"&apiKey={settings.massive_api_key}"
        )
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url)
            if resp.status_code != 200:
                return None
            data = resp.json()
            results = data.get("results", [])
            return len(results) if isinstance(results, list) else 0
        except Exception:
            return None

    async def _fetch_news_count_finnhub(self, symbol: str) -> int | None:
        """Fetch news count from Finnhub /company-news (for .TO stocks)."""
        if not settings.finnhub_api_key:
            return None

        finnhub_symbol = symbol.replace(".TO", "") if symbol.endswith(".TO") else symbol
        today = date.today()
        from_date = (today - timedelta(days=3)).isoformat()
        to_date = today.isoformat()
        url = (
            f"https://finnhub.io/api/v1/company-news"
            f"?symbol={finnhub_symbol}&from={from_date}&to={to_date}"
            f"&token={settings.finnhub_api_key}"
        )
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url)
            if resp.status_code != 200:
                return None
            articles = resp.json()
            return len(articles) if isinstance(articles, list) else 0
        except Exception:
            return None

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
