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
        self.min_signal_strength: float = 1.4  # lowered after cluster decorrelation

        # Composite weights (must sum to 1.0)
        # Sentiment reduced from 0.3 -> 0.2 based on Tetlock (2007) — positive
        # news is largely priced in; technicals dominate swing trading edge.
        self.technical_weight: float = 0.6
        self.sentiment_weight: float = 0.2
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
        # Fetch 252 days for 200-day SMA + 52-week high/low (Minervini template)
        daily = await self.data.get_daily(symbol, days=252)

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

        # Use latest intraday price during market hours for live pricing,
        # fall back to last daily close after hours / weekends
        from app.engine.live_scanner import _is_market_hours
        if _is_market_hours():
            intraday = await self.data.get_intraday(symbol, bars=1)
            current_price = intraday[-1]["close"] if intraday else closes[-1]
        else:
            current_price = closes[-1]
        current_rsi = rsi[-1] if not np.isnan(rsi[-1]) else 50.0
        current_histogram = histogram[-1] if not np.isnan(histogram[-1]) else 0.0
        current_atr = atr[-1] if not np.isnan(atr[-1]) else current_price * 0.02
        current_vol_ratio = vol_ratio[-1] if not np.isnan(vol_ratio[-1]) else 1.0
        current_bb_pct_b = bb_pct_b[-1] if not np.isnan(bb_pct_b[-1]) else 0.5
        current_stoch_k = stoch_k[-1] if not np.isnan(stoch_k[-1]) else 50.0
        current_stoch_d = stoch_d[-1] if not np.isnan(stoch_d[-1]) else 50.0
        current_adx = adx[-1] if not np.isnan(adx[-1]) else 25.0

        # --- Weekly trend filter (uses daily bars — no extra API call) ---
        # Price vs 50-day EMA approximates the weekly trend.
        # BUY into a weekly downtrend = catching a falling knife.
        ema_50 = calc_ema(closes, 50)
        weekly_trend = "neutral"
        weekly_penalty = 0.0
        if not np.isnan(ema_50[-1]):
            pct_from_ema50 = (current_price - ema_50[-1]) / ema_50[-1] * 100
            if pct_from_ema50 < -8:
                weekly_trend = "strong_downtrend"
                weekly_penalty = -1.5  # heavy penalty — likely catching a knife
            elif pct_from_ema50 < -3:
                weekly_trend = "downtrend"
                weekly_penalty = -0.7
            elif pct_from_ema50 > 8:
                weekly_trend = "strong_uptrend"
                weekly_penalty = 0.5  # slight boost — riding momentum
            elif pct_from_ema50 > 3:
                weekly_trend = "uptrend"
                weekly_penalty = 0.3

        # --- 200-day SMA filter (Minervini/O'Neil) ---
        # Hard filter: no BUY signals when price is below the 200-day SMA.
        # Exception: range-bound markets (mean_reverting regime, ADX < 20).
        sma_200 = float(np.mean(closes[-200:])) if len(closes) >= 200 else None
        below_sma_200 = sma_200 is not None and current_price < sma_200

        # --- Minervini-relaxed trend template (long candidates only) ---
        # Stricter than the 200-day SMA filter alone. Stocks failing this are
        # structurally weak. Only checks LONG eligibility — SELL is unaffected.
        passes_trend_template = bool(self._check_trend_template(closes, float(current_price)))

        # --- Score technical signals (range: -5 to +5) ---
        tech_score, tech_reasons = self._score_technical(
            current_rsi, current_histogram, crossover, current_vol_ratio, current_price,
            current_bb_pct_b, current_stoch_k, current_adx, rsi_divergence,
        )

        # Apply weekly trend adjustment
        if weekly_penalty != 0.0:
            tech_score += weekly_penalty
            tech_score = max(-5.0, min(5.0, tech_score))
            if weekly_penalty < 0:
                tech_reasons.append(f"Weekly {weekly_trend} — signal discounted")
            else:
                tech_reasons.append(f"Weekly {weekly_trend} — signal boosted")

        # --- Sentiment: Massive for US, Finnhub for .TO ---
        is_tsx = symbol.endswith(".TO")
        sentiment_provider = self._finnhub_sentiment if is_tsx else self._massive_sentiment
        if sentiment_provider is not None:
            sentiment_data = await sentiment_provider.get_sentiment(symbol)
            sentiment_score = sentiment_data["score"]
            sentiment_reasons = sentiment_data["reasons"]
        else:
            sentiment_score = 0.0
            sentiment_reasons = ["No sentiment provider configured"]

        # Asymmetric sentiment scoring (Tetlock 2007):
        #   - Negative sentiment is 2-3x more informative than positive
        #   - Extreme positive sentiment (>2.5) is often contrarian (priced in)
        if sentiment_score < 0:
            sentiment_score *= 1.5
            sentiment_reasons.append("Negative sentiment amplified (1.5x)")
        elif sentiment_score > 2.5:
            sentiment_score *= 0.7
            sentiment_reasons.append("Extreme positive sentiment discounted (0.7x — contrarian)")
        # Re-clamp to -3..+3 range after asymmetric adjustment
        sentiment_score = max(-3.0, min(3.0, sentiment_score))
        if self._fundamentals is not None:
            fundamental_data = await self._fundamentals.get_fundamentals(symbol)
            fundamental_score = fundamental_data["score"]
            fundamental_reasons = fundamental_data["reasons"]
        else:
            fundamental_score = 0.0
            fundamental_reasons = ["No fundamental provider configured"]

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
            # 200-day SMA hard filter — no BUY in structural downtrend.
            # Exception: range-bound markets (low ADX < 20).
            if below_sma_200 and current_adx >= 20:
                tech_reasons.append(
                    f"Below 200-day SMA (${sma_200:.2f}) — no BUY in downtrend"
                )
            elif not passes_trend_template:
                tech_reasons.append(
                    "Fails Minervini trend template — no BUY (structurally weak)"
                )
            else:
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

        # --- Position sizing (Van Tharp fixed fractional risk + conviction overlay) ---
        position_sizing = self._compute_position_size(
            current_price, stop_loss, conviction, signal_type,
        )

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
            "position_sizing": position_sizing,
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
        Cluster-based technical scoring on -5 to +5 scale.

        Indicators are grouped into independent clusters. Within each cluster,
        we take the strongest signal (by absolute value) rather than summing —
        this avoids triple-counting correlated indicators.

        Clusters (max contribution):
          - Momentum:      max(RSI, Stochastic)   ±2.0
          - Trend:         max(MACD, EMA cross)    ±2.0
          - Volatility:    Bollinger %B           ±1.0
          - Trend strength: ADX (additive)         ±0.5
          - Divergence:    RSI divergence          ±1.5
          - Volume:        vol_ratio (multiplier)  0.6x-1.3x

        Volume is the ONLY multiplier — it confirms direction of the base signal.
        ADX is additive (used to be multiplier) — avoids non-linear score swings.
        """
        reasons: list[str] = []

        # --- Momentum cluster: RSI + Stochastic (take stronger) ---
        rsi_contribution = 0.0
        if rsi < self.config.rsi_oversold:
            rsi_contribution = 2.0
            rsi_reason = f"RSI oversold ({rsi:.1f})"
        elif rsi < 40:
            rsi_contribution = 1.0
            rsi_reason = f"RSI approaching oversold ({rsi:.1f})"
        elif rsi > self.config.rsi_overbought:
            rsi_contribution = -2.0
            rsi_reason = f"RSI overbought ({rsi:.1f})"
        elif rsi > 60:
            rsi_contribution = -1.0
            rsi_reason = f"RSI approaching overbought ({rsi:.1f})"
        else:
            rsi_reason = ""

        stoch_contribution = 0.0
        if stoch_k < 20:
            stoch_contribution = 1.5
            stoch_reason = f"Stochastic oversold (%K={stoch_k:.1f})"
        elif stoch_k < 30:
            stoch_contribution = 0.75
            stoch_reason = f"Stochastic approaching oversold (%K={stoch_k:.1f})"
        elif stoch_k > 80:
            stoch_contribution = -1.5
            stoch_reason = f"Stochastic overbought (%K={stoch_k:.1f})"
        elif stoch_k > 70:
            stoch_contribution = -0.75
            stoch_reason = f"Stochastic approaching overbought (%K={stoch_k:.1f})"
        else:
            stoch_reason = ""

        # Take the stronger momentum signal (by absolute value), capped at ±2.0
        if abs(rsi_contribution) >= abs(stoch_contribution):
            momentum_score = rsi_contribution
            if rsi_reason:
                reasons.append(rsi_reason)
        else:
            momentum_score = stoch_contribution
            if stoch_reason:
                reasons.append(stoch_reason)
        momentum_score = max(-2.0, min(2.0, momentum_score))

        # --- Trend cluster: MACD + EMA crossover (take stronger) ---
        # MACD: normalize by ATR instead of price to avoid price-level bias
        # (but we don't have ATR here yet — fall back to price normalization for now)
        macd_pct = (macd_hist / current_price) * 100 if current_price > 0 else 0
        macd_contribution = 0.0
        macd_reason = ""
        if macd_pct > 0:
            macd_contribution = min(macd_pct * 2.0, 2.0)
            macd_reason = f"MACD bullish ({macd_pct:.2f}% of price)"
        elif macd_pct < 0:
            macd_contribution = max(macd_pct * 2.0, -2.0)
            macd_reason = f"MACD bearish ({macd_pct:.2f}% of price)"

        ema_contribution = 0.0
        ema_reason = ""
        if crossover["crossover"] == "bullish":
            if crossover["just_crossed"]:
                ema_contribution = 1.5
                ema_reason = "Bullish EMA crossover (fresh)"
            else:
                ema_contribution = 0.5
                ema_reason = "Bullish EMA trend"
        elif crossover["crossover"] == "bearish":
            if crossover["just_crossed"]:
                ema_contribution = -1.5
                ema_reason = "Bearish EMA crossover (fresh)"
            else:
                ema_contribution = -0.5
                ema_reason = "Bearish EMA trend"

        # Take the stronger trend signal
        if abs(macd_contribution) >= abs(ema_contribution):
            trend_score = macd_contribution
            if macd_reason:
                reasons.append(macd_reason)
        else:
            trend_score = ema_contribution
            if ema_reason:
                reasons.append(ema_reason)
        trend_score = max(-2.0, min(2.0, trend_score))

        # --- Volatility cluster: Bollinger %B (±1.0) ---
        vol_score = 0.0
        if bb_pct_b < 0.0:
            vol_score = 1.0
            reasons.append(f"Below lower Bollinger Band (%B={bb_pct_b:.2f})")
        elif bb_pct_b < 0.2:
            vol_score = 0.5
            reasons.append(f"Near lower Bollinger Band (%B={bb_pct_b:.2f})")
        elif bb_pct_b > 1.0:
            vol_score = -1.0
            reasons.append(f"Above upper Bollinger Band (%B={bb_pct_b:.2f})")
        elif bb_pct_b > 0.8:
            vol_score = -0.5
            reasons.append(f"Near upper Bollinger Band (%B={bb_pct_b:.2f})")

        # --- Trend strength (ADX) — ADDITIVE, not multiplicative ---
        # Strong ADX reinforces the existing directional score; weak ADX slightly discounts it.
        adx_score = 0.0
        if adx > 40:
            # Strong trend — small boost in the direction already established
            base_direction = momentum_score + trend_score
            if base_direction > 0:
                adx_score = 0.5
                reasons.append(f"Strong trend confirms bullish (ADX={adx:.1f})")
            elif base_direction < 0:
                adx_score = -0.5
                reasons.append(f"Strong trend confirms bearish (ADX={adx:.1f})")
        elif adx < 20:
            # Weak trend — slight discount in the direction already established
            base_direction = momentum_score + trend_score
            if base_direction > 0:
                adx_score = -0.3
                reasons.append(f"Weak trend discounts bullish (ADX={adx:.1f})")
            elif base_direction < 0:
                adx_score = 0.3
                reasons.append(f"Weak trend discounts bearish (ADX={adx:.1f})")

        # --- Divergence cluster (±1.5) ---
        div_score = 0.0
        if divergence and divergence.get("type") != "none":
            div_conf = divergence.get("confidence", 0)
            if div_conf >= 0.3:
                if divergence["type"] == "bullish":
                    div_score = 1.5 * div_conf
                    reasons.append(f"Bullish RSI divergence (conf={div_conf:.0%})")
                elif divergence["type"] == "bearish":
                    div_score = -1.5 * div_conf
                    reasons.append(f"Bearish RSI divergence (conf={div_conf:.0%})")

        # --- Base score = sum of independent clusters ---
        score = momentum_score + trend_score + vol_score + adx_score + div_score

        # --- Volume: multiplicative confirmation (the ONLY multiplier) ---
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

    def _check_trend_template(self, closes: np.ndarray, current_price: float) -> bool:
        """
        Minervini-relaxed trend template for swing trading long candidates.

        Stocks failing this check are structurally weak and unlikely to be
        good long setups. Used as a hard filter on BUY signals.

        Criteria (must ALL pass):
          1. Price > 50-day SMA  (short-term uptrend)
          2. Price > 150-day SMA (medium-term uptrend)
          3. 50-day SMA > 150-day SMA (proper MA stacking)
          4. Price within 25% of 52-week high (not bombed out)
          5. Price >= 20% above 52-week low (clear distance from bottom)

        Returns True if all criteria pass, False otherwise (fail-closed:
        insufficient data also returns False).
        """
        if len(closes) < 200:
            return False

        sma_50 = float(np.mean(closes[-50:]))
        sma_150 = float(np.mean(closes[-150:]))

        lookback = min(252, len(closes))
        recent = closes[-lookback:]
        week52_high = float(np.max(recent))
        week52_low = float(np.min(recent))

        # 1. Above 50-day SMA
        if current_price <= sma_50:
            return False
        # 2. Above 150-day SMA
        if current_price <= sma_150:
            return False
        # 3. 50-day above 150-day (MA stacking)
        if sma_50 <= sma_150:
            return False
        # 4. Within 25% of 52-week high
        if current_price < week52_high * 0.75:
            return False
        # 5. At least 20% above 52-week low
        if week52_low > 0 and current_price < week52_low * 1.20:
            return False

        return True

    def _compute_position_size(
        self,
        entry_price: float,
        stop_loss: float,
        conviction: float,
        signal_type: str,
    ) -> dict:
        """
        Van Tharp fixed fractional risk position sizing with conviction overlay.

        Formula:
            risk_dollars = portfolio * (risk_per_trade_pct / 100)
            base_shares = risk_dollars / (entry - stop)
            adjusted = base * (1 + conviction_factor * 0.25)
            capped = min(adjusted, max_position_value / entry)

        Conviction overlay (AQR research): scale base position by ±25% based on
        signal strength. A conviction of 3.0 (strong) adds 25%; 1.0 adds 8%.
        Capped at max_position_pct of portfolio.
        """
        portfolio = settings.portfolio_size_cad
        risk_pct = settings.risk_per_trade_pct
        max_pos_pct = settings.max_position_pct

        risk_dollars = portfolio * (risk_pct / 100)
        max_position_value = portfolio * (max_pos_pct / 100)

        # Per-share risk (always positive — distance between entry and stop)
        per_share_risk = abs(entry_price - stop_loss)

        # Guard against degenerate cases
        if per_share_risk <= 0 or entry_price <= 0:
            return {
                "shares": 0,
                "position_value": 0.0,
                "risk_amount": 0.0,
                "risk_pct_of_portfolio": 0.0,
                "conviction_multiplier": 1.0,
                "capped_at_max_position": False,
            }

        # Base size from fixed fractional risk
        base_shares = risk_dollars / per_share_risk

        # Conviction overlay: ±25% based on conviction magnitude (clamped 0-3)
        # conviction 0 → 1.0x, conviction 3 → 1.25x, conviction -3 → 0.75x for SELL
        conviction_strength = min(3.0, abs(conviction)) / 3.0  # 0-1
        conviction_multiplier = 1.0 + (conviction_strength - 0.5) * 0.5  # 0.75-1.25

        adjusted_shares = base_shares * conviction_multiplier

        # Cap at max position size — cast everything to native Python types
        # to avoid numpy.bool/numpy.float in JSON-serialized output.
        max_shares = float(max_position_value) / float(entry_price)
        capped = bool(adjusted_shares > max_shares)
        final_shares = int(min(adjusted_shares, max_shares))

        position_value = float(final_shares) * float(entry_price)
        actual_risk = float(final_shares) * float(per_share_risk)

        return {
            "shares": final_shares,
            "position_value": round(position_value, 2),
            "risk_amount": round(actual_risk, 2),
            "risk_pct_of_portfolio": round(actual_risk / portfolio * 100, 2) if portfolio > 0 else 0.0,
            "conviction_multiplier": round(conviction_multiplier, 2),
            "capped_at_max_position": capped,
        }

