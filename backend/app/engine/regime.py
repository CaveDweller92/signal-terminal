"""
Regime Detector — identifies the current market regime.

Regimes (from the spec):
  - trending_up:      sustained upward movement, momentum strategies work
  - trending_down:    sustained downward movement, short or stay out
  - mean_reverting:   range-bound, buy dips / sell rips
  - volatile_choppy:  high volatility with no clear direction, reduce size
  - low_volatility:   quiet market, signals are less frequent but reliable

Phase 1: Simple heuristic-based detection using trend slope + volatility.
Phase 5: Replaced by HMM (Hidden Markov Model) trained on historical data.
"""

import numpy as np

from app.engine.data_provider import DataProvider
from app.engine.indicators import calc_atr, calc_ema


class RegimeDetector:
    def __init__(self, data_provider: DataProvider):
        self.data = data_provider

    async def detect(self, symbol: str = "SPY") -> dict:
        """
        Detect the current market regime using a broad market proxy.

        Uses SPY by default because regime is a market-level concept,
        not per-stock. Individual stock analysis happens in the analyzer.

        Returns:
            {regime, confidence, features, detection_method}
        """
        daily = await self.data.get_daily(symbol, days=60)

        closes = np.array([b["close"] for b in daily])
        highs = np.array([b["high"] for b in daily])
        lows = np.array([b["low"] for b in daily])

        # --- Feature 1: Trend direction & strength ---
        # Linear regression slope over last 20 days, normalized by price
        lookback = 20
        recent = closes[-lookback:]
        x = np.arange(lookback)
        slope = np.polyfit(x, recent, 1)[0]
        norm_slope = slope / np.mean(recent)  # Normalize: +0.005 = ~0.5%/day uptrend

        # --- Feature 2: Volatility level ---
        # ATR as percentage of price (ATR% over last 14 days)
        atr = calc_atr(highs, lows, closes)
        current_atr = atr[-1] if not np.isnan(atr[-1]) else np.std(closes[-14:])
        atr_pct = current_atr / closes[-1]

        # Historical ATR% for relative comparison
        recent_atr_values = atr[-20:]
        valid_atr = recent_atr_values[~np.isnan(recent_atr_values)]
        atr_trend = 0.0
        if len(valid_atr) >= 5:
            atr_trend = (valid_atr[-1] - valid_atr[0]) / valid_atr[0]  # Rising or falling vol

        # --- Feature 3: Mean-reversion signal ---
        # Price relative to 20-day EMA — if it keeps bouncing around the EMA, it's ranging
        ema20 = calc_ema(closes, 20)
        valid_ema = ema20[-lookback:]
        valid_ema = valid_ema[~np.isnan(valid_ema)]
        valid_close = closes[-len(valid_ema):]

        crossings = 0
        if len(valid_ema) > 1:
            above = valid_close > valid_ema
            crossings = int(np.sum(np.diff(above.astype(int)) != 0))

        # --- Classification logic ---
        regime, confidence = self._classify(norm_slope, atr_pct, atr_trend, crossings)

        return {
            "regime": regime,
            "confidence": round(float(confidence), 3),
            "features": {
                "trend_slope": round(float(norm_slope), 6),
                "atr_pct": round(float(atr_pct), 4),
                "atr_trend": round(float(atr_trend), 4),
                "ema_crossings": crossings,
            },
            "detection_method": "heuristic",
        }

    def _classify(
        self,
        norm_slope: float,
        atr_pct: float,
        atr_trend: float,
        ema_crossings: int,
    ) -> tuple[str, float]:
        """
        Rule-based regime classification.

        Thresholds are intentionally simple — the HMM in Phase 5
        will learn these boundaries from data instead.
        """
        # High volatility + no clear trend = choppy
        if atr_pct > 0.03 and abs(norm_slope) < 0.002:
            confidence = min(0.9, 0.5 + atr_pct * 10)
            return "volatile_choppy", confidence

        # Low volatility
        if atr_pct < 0.01:
            confidence = min(0.9, 0.5 + (0.01 - atr_pct) * 50)
            return "low_volatility", confidence

        # Many EMA crossings = mean reverting (range-bound)
        if ema_crossings >= 6 and abs(norm_slope) < 0.003:
            confidence = min(0.85, 0.4 + ema_crossings * 0.05)
            return "mean_reverting", confidence

        # Strong uptrend
        if norm_slope > 0.002:
            confidence = min(0.9, 0.4 + norm_slope * 100)
            return "trending_up", confidence

        # Strong downtrend
        if norm_slope < -0.002:
            confidence = min(0.9, 0.4 + abs(norm_slope) * 100)
            return "trending_down", confidence

        # Default: low confidence mean reverting
        return "mean_reverting", 0.4
