"""
Signal Analyzer — the core decision engine.

Takes raw OHLCV data from the DataProvider, runs it through technical
indicators, and produces BUY/SELL/HOLD signals with conviction scores.

Conviction is a weighted composite:
  conviction = tech_score * tech_weight
             + sentiment_score * sentiment_weight
             + fundamental_score * fundamental_weight

Swing trading mode: all indicators run on daily bars.
"""

import logging

import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)
from app.engine.data_provider import DataProvider
from app.engine.fundamental_analyzer import FundamentalAnalyzer
from app.engine.massive_sentiment import MassiveSentimentAnalyzer
from app.engine.sentiment_analyzer import SentimentAnalyzer
from app.engine.indicators import (
    calc_adx,
    calc_atr,
    calc_bollinger_bands,
    calc_ema,
    calc_macd,
    calc_rsi,
    calc_stochastic,
    calc_volume_ratio,
    detect_divergence,
    detect_ema_crossover,
)


class AnalyzerConfig:
    """Strategy parameters — these get tuned by the adaptive system."""

    def __init__(self, overrides: dict | None = None):
        self.rsi_period: int = 14
        self.rsi_overbought: int = 70
        self.rsi_oversold: int = 30
        self.ema_fast: int = 10   # 10-day EMA (swing)
        self.ema_slow: int = 50   # 50-day EMA (swing)
        self.macd_fast: int = 12
        self.macd_slow: int = 26
        self.macd_signal: int = 9
        self.volume_multiplier: float = 1.3  # daily volume spikes are less extreme
        self.min_signal_strength: float = 1.5  # swing signals develop gradually

        # Composite weights (must sum to 1.0)
        self.technical_weight: float = 0.5
        self.sentiment_weight: float = 0.3
        self.fundamental_weight: float = 0.2

        # Exit levels
        self.atr_stop_multiplier: float = settings.default_atr_multiplier_stop
        self.atr_target_multiplier: float = settings.default_atr_multiplier_target
        self.default_stop_loss_pct: float = settings.default_stop_loss_pct
        self.default_profit_target_pct: float = settings.default_profit_target_pct

        # Apply overrides from ParameterSnapshot (regime-tuned values)
        if overrides:
            for key, value in overrides.items():
                if hasattr(self, key) and value is not None:
                    setattr(self, key, value)


# Module-level singletons — preserves in-memory caches across requests
# US stocks use Massive (unlimited); .TO stocks use Finnhub (low volume, within limits)
_massive_sentiment_singleton: MassiveSentimentAnalyzer | None = None
_finnhub_sentiment_singleton: SentimentAnalyzer | None = None
_fundamental_singleton: FundamentalAnalyzer | None = None


def _get_massive_sentiment() -> MassiveSentimentAnalyzer | None:
    global _massive_sentiment_singleton
    if settings.massive_api_key:
        if _massive_sentiment_singleton is None:
            _massive_sentiment_singleton = MassiveSentimentAnalyzer(
                settings.massive_api_key, settings.anthropic_api_key
            )
        return _massive_sentiment_singleton
    return None


def _get_finnhub_sentiment() -> SentimentAnalyzer | None:
    global _finnhub_sentiment_singleton
    if settings.finnhub_api_key and settings.anthropic_api_key:
        if _finnhub_sentiment_singleton is None:
            _finnhub_sentiment_singleton = SentimentAnalyzer(settings.finnhub_api_key, settings.anthropic_api_key)
        return _finnhub_sentiment_singleton
    return None


def _get_fundamentals() -> FundamentalAnalyzer | None:
    global _fundamental_singleton
    if settings.finnhub_api_key:
        if _fundamental_singleton is None:
            _fundamental_singleton = FundamentalAnalyzer(settings.finnhub_api_key)
        return _fundamental_singleton
    return None


class SignalAnalyzer:
    def __init__(self, data_provider: DataProvider, config: AnalyzerConfig | None = None):
        self.data = data_provider
        self.config = config or AnalyzerConfig()
        self._massive_sentiment = _get_massive_sentiment()
        self._finnhub_sentiment = _get_finnhub_sentiment()
        self._fundamentals = _get_fundamentals()

    async def analyze(self, symbol: str) -> dict:
        """
        Run full analysis on a symbol and return a signal dict.

        Uses daily bars for all technical indicators (swing trading).
        Intraday bars are only used as a fallback for current price.
        """
        daily = await self.data.get_daily(symbol)

        if not daily or len(daily) < 20:
            logger.warning(f"Analyzer: insufficient daily data for {symbol} — skipping")
            return None

        closes = np.array([b["close"] for b in daily])
        highs = np.array([b["high"] for b in daily])
        lows = np.array([b["low"] for b in daily])
        volumes = np.array([b["volume"] for b in daily], dtype=float)

        # --- Technical indicators (all on daily bars) ---
        rsi = calc_rsi(closes, self.config.rsi_period)
        macd_line, signal_line, histogram = calc_macd(
            closes, self.config.macd_fast, self.config.macd_slow, self.config.macd_signal
        )
        atr = calc_atr(highs, lows, closes)
        vol_ratio = calc_volume_ratio(volumes)
        crossover = detect_ema_crossover(closes, self.config.ema_fast, self.config.ema_slow)

        # New indicators
        bb_upper, bb_middle, bb_lower, bb_pct_b = calc_bollinger_bands(closes)
        stoch_k, stoch_d = calc_stochastic(highs, lows, closes)
        adx = calc_adx(highs, lows, closes)
        rsi_divergence = detect_divergence(closes, rsi)

        current_price = closes[-1]
        current_rsi = rsi[-1] if not np.isnan(rsi[-1]) else 50.0
        current_histogram = histogram[-1] if not np.isnan(histogram[-1]) else 0.0
        current_atr = atr[-1] if not np.isnan(atr[-1]) else current_price * 0.02
        current_vol_ratio = vol_ratio[-1] if not np.isnan(vol_ratio[-1]) else 1.0
        current_bb_pct_b = bb_pct_b[-1] if not np.isnan(bb_pct_b[-1]) else 0.5
        current_stoch_k = stoch_k[-1] if not np.isnan(stoch_k[-1]) else 50.0
        current_stoch_d = stoch_d[-1] if not np.isnan(stoch_d[-1]) else 50.0
        current_adx = adx[-1] if not np.isnan(adx[-1]) else 25.0

        # --- Score technical signals (range: -5 to +5) ---
        tech_score, tech_reasons = self._score_technical(
            current_rsi, current_histogram, crossover, current_vol_ratio, current_price,
            current_bb_pct_b, current_stoch_k, current_adx, rsi_divergence,
        )

        # --- Sentiment: Massive for US, Finnhub for .TO ---
        is_tsx = symbol.endswith(".TO")
        sentiment_provider = self._finnhub_sentiment if is_tsx else self._massive_sentiment
        if sentiment_provider is not None:
            sentiment_data = await sentiment_provider.get_sentiment(symbol)
            sentiment_score = sentiment_data["score"]
            sentiment_reasons = sentiment_data["reasons"]
        else:
            sentiment_score = self._simulated_sentiment(symbol)
            sentiment_reasons = self._sentiment_reasons(sentiment_score)
        if self._fundamentals is not None:
            fundamental_data = await self._fundamentals.get_fundamentals(symbol)
            fundamental_score = fundamental_data["score"]
            fundamental_reasons = fundamental_data["reasons"]
        else:
            fundamental_score = self._simulated_fundamental(symbol)
            fundamental_reasons = self._fundamental_reasons(fundamental_score)

        # --- Composite conviction ---
        conviction = (
            tech_score * self.config.technical_weight
            + sentiment_score * self.config.sentiment_weight
            + fundamental_score * self.config.fundamental_weight
        )

        # --- Exit levels (must be computed before R:R filter) ---
        stop_loss = round(float(current_price - current_atr * self.config.atr_stop_multiplier), 2)
        profit_target = round(float(current_price + current_atr * self.config.atr_target_multiplier), 2)

        # Fallback to percentage-based if ATR levels are unreasonable
        pct_stop = round(current_price * (1 - self.config.default_stop_loss_pct / 100), 2)
        pct_target = round(current_price * (1 + self.config.default_profit_target_pct / 100), 2)

        if stop_loss >= current_price:
            stop_loss = pct_stop
        if profit_target <= current_price:
            profit_target = pct_target

        # --- Determine signal type with risk/reward filter ---
        signal_type = "HOLD"
        if conviction >= self.config.min_signal_strength:
            # Check risk/reward: potential reward must be >= 1.5× potential risk
            reward = profit_target - current_price
            risk = current_price - stop_loss
            if risk > 0 and reward / risk >= 1.5:
                signal_type = "BUY"
            elif risk <= 0:
                signal_type = "BUY"  # stop below zero edge case, allow it
            else:
                tech_reasons.append(f"R:R too low ({reward/risk:.1f}:1, need 1.5:1)")
        elif conviction <= -self.config.min_signal_strength:
            signal_type = "SELL"

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
                "bollinger_pct_b": round(float(current_bb_pct_b), 3),
                "stochastic_k": round(float(current_stoch_k), 2),
                "stochastic_d": round(float(current_stoch_d), 2),
                "adx": round(float(current_adx), 2),
                "divergence": rsi_divergence,
            },
        }

    def _score_technical(
        self,
        rsi: float,
        macd_hist: float,
        crossover: dict,
        vol_ratio: float,
        current_price: float = 1.0,
        bb_pct_b: float = 0.5,
        stoch_k: float = 50.0,
        adx: float = 25.0,
        divergence: dict | None = None,
    ) -> tuple[float, list[str]]:
        """
        Score technical indicators on a -5 to +5 scale.
        Each indicator contributes a sub-score; they're summed and clamped.
        Calibrated for daily bar data (swing trading).
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

        # MACD histogram — normalize by price for comparable scale across stocks
        macd_pct = (macd_hist / current_price) * 100 if current_price > 0 else 0
        if macd_pct > 0:
            macd_score = min(macd_pct * 2.0, 2.0)
            score += macd_score
            reasons.append(f"MACD bullish ({macd_pct:.2f}% of price)")
        elif macd_pct < 0:
            macd_score = min(abs(macd_pct) * 2.0, 2.0)
            score -= macd_score
            reasons.append(f"MACD bearish ({macd_pct:.2f}% of price)")

        # EMA crossover (10/50 for swing) — reduced fresh cross bonus from 2.0 to 1.5
        if crossover["crossover"] == "bullish":
            if crossover["just_crossed"]:
                score += 1.5
                reasons.append("Bullish EMA crossover (fresh)")
            else:
                score += 0.5
                reasons.append("Bullish EMA trend")
        elif crossover["crossover"] == "bearish":
            if crossover["just_crossed"]:
                score -= 1.5
                reasons.append("Bearish EMA crossover (fresh)")
            else:
                score -= 0.5
                reasons.append("Bearish EMA trend")

        # Bollinger Bands %B (±1.0 max)
        if bb_pct_b < 0.0:
            score += 1.0
            reasons.append(f"Below lower Bollinger Band (%B={bb_pct_b:.2f})")
        elif bb_pct_b < 0.2:
            score += 0.5
            reasons.append(f"Near lower Bollinger Band (%B={bb_pct_b:.2f})")
        elif bb_pct_b > 1.0:
            score -= 1.0
            reasons.append(f"Above upper Bollinger Band (%B={bb_pct_b:.2f})")
        elif bb_pct_b > 0.8:
            score -= 0.5
            reasons.append(f"Near upper Bollinger Band (%B={bb_pct_b:.2f})")

        # Stochastic %K (±1.0 max)
        if stoch_k < 20:
            score += 1.0
            reasons.append(f"Stochastic oversold (%K={stoch_k:.1f})")
        elif stoch_k > 80:
            score -= 1.0
            reasons.append(f"Stochastic overbought (%K={stoch_k:.1f})")

        # ADX — trend strength multiplier (0.8x to 1.2x)
        if adx < 20:
            score *= 0.8
            reasons.append(f"Weak trend (ADX={adx:.1f}) — signal discounted")
        elif adx > 40:
            score *= 1.2
            reasons.append(f"Strong trend (ADX={adx:.1f}) — signal boosted")

        # Divergence (±1.5)
        if divergence and divergence.get("type") != "none":
            div_conf = divergence.get("confidence", 0)
            if div_conf >= 0.3:
                if divergence["type"] == "bullish":
                    score += 1.5 * div_conf
                    reasons.append(f"Bullish RSI divergence (conf={div_conf:.0%})")
                elif divergence["type"] == "bearish":
                    score -= 1.5 * div_conf
                    reasons.append(f"Bearish RSI divergence (conf={div_conf:.0%})")

        # Volume confirmation — multiplicative, not additive
        if vol_ratio >= 2.0:
            score *= 1.3
            reasons.append(f"Volume spike ({vol_ratio:.1f}x avg) confirms move")
        elif vol_ratio >= self.config.volume_multiplier:
            reasons.append(f"Above-average volume ({vol_ratio:.1f}x)")
        elif vol_ratio < 0.5:
            score *= 0.6
            reasons.append(f"Low volume ({vol_ratio:.1f}x) — signal discounted")

        # Clamp to range
        score = max(-5.0, min(5.0, score))

        return score, reasons

    def _simulated_sentiment(self, symbol: str) -> float:
        h = hash(f"sentiment_{symbol}") % 1000
        return round((h / 1000) * 6 - 3, 2)

    def _simulated_fundamental(self, symbol: str) -> float:
        h = hash(f"fundamental_{symbol}") % 1000
        return round((h / 1000) * 4 - 2, 2)

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
