"""
Pre-market Screener — scans the universe and surfaces the top 30 stocks.

Runs daily at 5:00 AM ET. Scores each stock on 6 dimensions:
  1. Volume score     — relative volume vs 20-day average
  2. Gap score        — pre-market gap percentage
  3. Technical score  — RSI, EMA trend, MACD alignment
  4. Fundamental score — simulated in Phase 1
  5. News score       — simulated in Phase 1
  6. Sector score     — sector momentum relative to market

Composite = weighted sum of all 6 scores.
Top 30 by composite score are saved to screener_results.
"""

from datetime import date, datetime

import numpy as np
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.data_provider import DataProvider
from app.engine.indicators import calc_rsi, calc_ema, calc_macd, calc_volume_ratio
from app.models.screener_result import ScreenerResult
from app.models.stock_universe import StockUniverse


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

    def __init__(self, data_provider: DataProvider):
        self.data = data_provider

    async def scan(
        self,
        stocks: list[StockUniverse],
        db: AsyncSession,
        top_n: int = 30,
    ) -> list[ScreenerResult]:
        """
        Scan all stocks, score them, save top N to DB.
        Returns the top N ScreenerResult objects.
        """
        today = date.today()

        # Clear today's existing results (idempotent)
        await db.execute(
            delete(ScreenerResult).where(ScreenerResult.scan_date == today)
        )

        scored: list[dict] = []

        for stock in stocks:
            try:
                scores = await self._score_stock(stock)
                scores["symbol"] = stock.symbol
                scores["exchange"] = stock.exchange
                scores["sector_name"] = stock.sector
                scored.append(scores)
            except Exception:
                continue  # Skip stocks that fail (bad data, etc.)

        # Sort by composite score descending
        scored.sort(key=lambda s: s["composite"], reverse=True)

        # Save top N
        results: list[ScreenerResult] = []
        for entry in scored[:top_n]:
            result = ScreenerResult(
                scan_date=today,
                symbol=entry["symbol"],
                exchange=entry["exchange"],
                composite_score=round(entry["composite"], 4),
                volume_score=round(entry["volume"], 4),
                gap_score=round(entry["gap"], 4),
                technical_score=round(entry["technical"], 4),
                fundamental_score=round(entry["fundamental"], 4),
                news_score=round(entry["news"], 4),
                sector_score=round(entry["sector"], 4),
                premarket_gap_pct=round(entry.get("gap_pct", 0), 4),
                relative_volume=round(entry.get("rel_volume", 1), 2),
                sector=entry["sector_name"],
                has_catalyst=entry.get("has_catalyst", False),
            )
            db.add(result)
            results.append(result)

        await db.commit()
        return results

    async def _score_stock(self, stock: StockUniverse) -> dict:
        """Score a single stock on all 6 dimensions (0-10 scale each)."""
        bars = await self.data.get_intraday(stock.symbol)
        daily = await self.data.get_daily(stock.symbol)

        closes = np.array([b["close"] for b in bars])
        volumes = np.array([b["volume"] for b in bars], dtype=float)
        daily_closes = np.array([b["close"] for b in daily])

        # 1. Volume score — relative volume spike
        vol_ratio = calc_volume_ratio(volumes)
        current_vol = float(vol_ratio[-1]) if not np.isnan(vol_ratio[-1]) else 1.0
        volume_score = min(10, current_vol * 3)  # 3x avg = score 9

        # 2. Gap score — simulated pre-market gap
        if len(daily_closes) >= 2:
            gap_pct = ((closes[0] - daily_closes[-2]) / daily_closes[-2]) * 100
        else:
            gap_pct = 0.0
        gap_score = min(10, abs(gap_pct) * 2)  # 5% gap = score 10

        # 3. Technical score — RSI + EMA + MACD alignment
        rsi = calc_rsi(daily_closes)
        current_rsi = float(rsi[-1]) if not np.isnan(rsi[-1]) else 50.0

        ema_fast = calc_ema(daily_closes, 9)
        ema_slow = calc_ema(daily_closes, 21)
        ema_bullish = (
            not np.isnan(ema_fast[-1])
            and not np.isnan(ema_slow[-1])
            and ema_fast[-1] > ema_slow[-1]
        )

        _, _, histogram = calc_macd(daily_closes)
        macd_bull = not np.isnan(histogram[-1]) and histogram[-1] > 0

        tech_score = 5.0  # Base
        if current_rsi < 35:
            tech_score += 2.5  # Oversold bounce opportunity
        elif current_rsi > 65:
            tech_score += 1.0  # Momentum
        if ema_bullish:
            tech_score += 1.5
        if macd_bull:
            tech_score += 1.0
        tech_score = min(10, tech_score)

        # 4. Fundamental score — simulated
        h = hash(f"fund_screen_{stock.symbol}") % 100
        fundamental_score = 3.0 + (h / 100) * 7.0  # Range 3-10

        # 5. News score — simulated
        h = hash(f"news_screen_{stock.symbol}") % 100
        news_score = 2.0 + (h / 100) * 8.0  # Range 2-10
        has_catalyst = h > 70

        # 6. Sector score — simulated sector momentum
        h = hash(f"sector_{stock.sector}_{date.today().isoformat()}") % 100
        sector_score = 2.0 + (h / 100) * 8.0

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
