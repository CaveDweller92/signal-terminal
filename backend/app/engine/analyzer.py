"""
Signal Analyzer — the core decision engine.

Takes raw OHLCV data from the DataProvider, runs it through technical
indicators, and produces BUY/SELL/HOLD signals with conviction scores.

Conviction is a weighted composite:
  conviction = tech_score * tech_weight
             + sentiment_score * sentiment_weight
             + fundamental_score * fundamental_weight

Phase 1: sentiment and fundamental scores are simulated.
Phase 3+ will plug in Claude sentiment analysis and real fundamentals.
"""

import logging

import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)
from app.engine.data_provider import DataProvider
from app.engine.sentiment_analyzer import SentimentAnalyzer
from app.engine.indicators import (
    calc_atr,
    calc_ema,
    calc_macd,
    calc_rsi,
    calc_volume_ratio,
    detect_ema_crossover,
)


class AnalyzerConfig:
    """Strategy parameters — these get tuned by the adaptive system in Phase 5."""

    def __init__(self):
        self.rsi_period: int = 14
        self.rsi_overbought: int = 70
        self.rsi_oversold: int = 30
        self.ema_fast: int = 9
        self.ema_slow: int = 21
        self.macd_fast: int = 12
        self.macd_slow: int = 26
        self.macd_signal: int = 9
        self.volume_multiplier: float = 1.5
        self.min_signal_strength: float = 2.0

        # Composite weights (must sum to 1.0)
        self.technical_weight: float = 0.5
        self.sentiment_weight: float = 0.3
        self.fundamental_weight: float = 0.2

        # Exit levels
        self.atr_stop_multiplier: float = settings.default_atr_multiplier_stop
        self.atr_target_multiplier: float = settings.default_atr_multiplier_target
        self.default_stop_loss_pct: float = settings.default_stop_loss_pct
        self.default_profit_target_pct: float = settings.default_profit_target_pct


class SignalAnalyzer:
    def __init__(self, data_provider: DataProvider, config: AnalyzerConfig | None = None):
        self.data = data_provider
        self.config = config or AnalyzerConfig()
        # Real sentiment when both keys are configured; simulated otherwise
        if settings.finnhub_api_key and settings.anthropic_api_key:
            self._sentiment = SentimentAnalyzer(settings.finnhub_api_key, settings.anthropic_api_key)
        else:
            self._sentiment = None

    async def analyze(self, symbol: str) -> dict:
        """
        Run full analysis on a symbol and return a signal dict.

        Returns:
            {
                symbol, signal_type, conviction, tech_score,
                sentiment_score, fundamental_score, price_at_signal,
                reasons, suggested_stop_loss, suggested_profit_target,
                atr_at_signal, indicators
            }
        """
        bars = await self.data.get_intraday(symbol)
        daily = await self.data.get_daily(symbol)

        if not bars or not daily:
            logger.warning(f"Analyzer: no data for {symbol} — skipping")
            return None

        closes = np.array([b["close"] for b in bars])
        highs = np.array([b["high"] for b in bars])
        lows = np.array([b["low"] for b in bars])
        volumes = np.array([b["volume"] for b in bars], dtype=float)

        daily_closes = np.array([b["close"] for b in daily])
        daily_highs = np.array([b["high"] for b in daily])
        daily_lows = np.array([b["low"] for b in daily])

        # --- Technical indicators ---
        rsi = calc_rsi(closes, self.config.rsi_period)
        macd_line, signal_line, histogram = calc_macd(
            closes, self.config.macd_fast, self.config.macd_slow, self.config.macd_signal
        )
        atr = calc_atr(daily_highs, daily_lows, daily_closes)
        vol_ratio = calc_volume_ratio(volumes)
        crossover = detect_ema_crossover(closes, self.config.ema_fast, self.config.ema_slow)

        current_price = closes[-1]
        current_rsi = rsi[-1] if not np.isnan(rsi[-1]) else 50.0
        current_histogram = histogram[-1] if not np.isnan(histogram[-1]) else 0.0
        current_atr = atr[-1] if not np.isnan(atr[-1]) else current_price * 0.02
        current_vol_ratio = vol_ratio[-1] if not np.isnan(vol_ratio[-1]) else 1.0

        # --- Score technical signals (range: -5 to +5) ---
        tech_score, tech_reasons = self._score_technical(
            current_rsi, current_histogram, crossover, current_vol_ratio
        )

        # --- Sentiment & fundamental ---
        if self._sentiment is not None:
            sentiment_data = await self._sentiment.get_sentiment(symbol)
            sentiment_score = sentiment_data["score"]
            sentiment_reasons = sentiment_data["reasons"]
        else:
            sentiment_score = self._simulated_sentiment(symbol)
            sentiment_reasons = self._sentiment_reasons(sentiment_score)
        fundamental_score = self._simulated_fundamental(symbol)
        fundamental_reasons = self._fundamental_reasons(fundamental_score)

        # --- Composite conviction ---
        conviction = (
            tech_score * self.config.technical_weight
            + sentiment_score * self.config.sentiment_weight
            + fundamental_score * self.config.fundamental_weight
        )

        # --- Determine signal type ---
        signal_type = "HOLD"
        if conviction >= self.config.min_signal_strength:
            signal_type = "BUY"
        elif conviction <= -self.config.min_signal_strength:
            signal_type = "SELL"

        # --- Exit levels ---
        stop_loss = round(float(current_price - current_atr * self.config.atr_stop_multiplier), 2)
        profit_target = round(float(current_price + current_atr * self.config.atr_target_multiplier), 2)

        # Fallback to percentage-based if ATR levels are unreasonable
        pct_stop = round(current_price * (1 - self.config.default_stop_loss_pct / 100), 2)
        pct_target = round(current_price * (1 + self.config.default_profit_target_pct / 100), 2)

        if stop_loss >= current_price:
            stop_loss = pct_stop
        if profit_target <= current_price:
            profit_target = pct_target

        return {
            "symbol": symbol,
            "signal_type": signal_type,
            "conviction": round(float(conviction), 3),
            "tech_score": round(float(tech_score), 3),
            "sentiment_score": round(float(sentiment_score), 3),
            "fundamental_score": round(float(fundamental_score), 3),
            "price_at_signal": round(float(current_price), 2),
            "suggested_stop_loss": stop_loss,
            "suggested_profit_target": profit_target,
            "atr_at_signal": round(float(current_atr), 4),
            "reasons": {
                "technical": tech_reasons,
                "sentiment": sentiment_reasons,
                "fundamental": fundamental_reasons,
            },
            "indicators": {
                "rsi": round(float(current_rsi), 2),
                "macd_histogram": round(float(current_histogram), 4),
                "ema_crossover": crossover["crossover"],
                "ema_just_crossed": crossover["just_crossed"],
                "volume_ratio": round(float(current_vol_ratio), 2),
                "atr": round(float(current_atr), 4),
            },
        }

    def _score_technical(
        self,
        rsi: float,
        macd_hist: float,
        crossover: dict,
        vol_ratio: float,
    ) -> tuple[float, list[str]]:
        """
        Score technical indicators on a -5 to +5 scale.
        Each indicator contributes a sub-score; they're summed and clamped.
        """
        score = 0.0
        reasons: list[str] = []

        # RSI
        if rsi < self.config.rsi_oversold:
            score += 2.0
            reasons.append(f"RSI oversold ({rsi:.1f})")
        elif rsi < 40:
            score += 1.0
            reasons.append(f"RSI approaching oversold ({rsi:.1f})")
        elif rsi > self.config.rsi_overbought:
            score -= 2.0
            reasons.append(f"RSI overbought ({rsi:.1f})")
        elif rsi > 60:
            score -= 1.0
            reasons.append(f"RSI approaching overbought ({rsi:.1f})")

        # MACD histogram
        if macd_hist > 0:
            score += min(macd_hist * 100, 2.0)  # Cap contribution
            reasons.append(f"MACD bullish (histogram {macd_hist:.4f})")
        elif macd_hist < 0:
            score -= min(abs(macd_hist) * 100, 2.0)
            reasons.append(f"MACD bearish (histogram {macd_hist:.4f})")

        # EMA crossover
        if crossover["crossover"] == "bullish":
            if crossover["just_crossed"]:
                score += 2.0
                reasons.append("Bullish EMA crossover (fresh)")
            else:
                score += 0.5
                reasons.append("Bullish EMA trend")
        elif crossover["crossover"] == "bearish":
            if crossover["just_crossed"]:
                score -= 2.0
                reasons.append("Bearish EMA crossover (fresh)")
            else:
                score -= 0.5
                reasons.append("Bearish EMA trend")

        # Volume confirmation
        if vol_ratio >= 2.0:
            # Amplify whatever direction we're leaning
            amplifier = 1.5 if score > 0 else -1.5 if score < 0 else 0
            score += amplifier
            reasons.append(f"Volume spike ({vol_ratio:.1f}x avg) confirms move")
        elif vol_ratio >= self.config.volume_multiplier:
            reasons.append(f"Above-average volume ({vol_ratio:.1f}x)")
        elif vol_ratio < 0.5:
            score *= 0.7  # Discount signal on thin volume
            reasons.append(f"Low volume ({vol_ratio:.1f}x) — signal discounted")

        # Clamp to range
        score = max(-5.0, min(5.0, score))

        return score, reasons

    def _simulated_sentiment(self, symbol: str) -> float:
        """Phase 1 placeholder — deterministic 'sentiment' from symbol hash."""
        h = hash(f"sentiment_{symbol}") % 1000
        return round((h / 1000) * 6 - 3, 2)  # Range: -3 to +3

    def _simulated_fundamental(self, symbol: str) -> float:
        """Phase 1 placeholder — deterministic 'fundamental' score."""
        h = hash(f"fundamental_{symbol}") % 1000
        return round((h / 1000) * 4 - 2, 2)  # Range: -2 to +2

    def _sentiment_reasons(self, score: float) -> list[str]:
        if score > 1:
            return ["Simulated positive sentiment"]
        elif score < -1:
            return ["Simulated negative sentiment"]
        return ["Simulated neutral sentiment"]

    def _fundamental_reasons(self, score: float) -> list[str]:
        if score > 0.5:
            return ["Simulated favorable fundamentals"]
        elif score < -0.5:
            return ["Simulated weak fundamentals"]
        return ["Simulated neutral fundamentals"]
