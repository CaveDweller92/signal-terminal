"""
Indicator Reversal Exit Strategy.

Exits when the same technical indicators that justified entry now flip:
- RSI crosses into overbought (for longs) or oversold (for shorts)
- EMA fast crosses below slow (bearish for longs)
- MACD histogram flips sign

Scoring: single flip = MEDIUM, multiple = HIGH.
"""

import numpy as np

from app.engine.indicators import calc_ema, calc_macd, calc_rsi
from app.models.position import Position
from app.positions.exit_strategies.base import ExitStrategy, ExitSignalResult, ExitUrgency


class IndicatorReversalStrategy(ExitStrategy):
    def __init__(self, config: dict | None = None):
        self.config = config or {}

    async def evaluate(
        self, position: Position, current_bar: dict, recent_bars: list[dict]
    ) -> ExitSignalResult | None:
        if len(recent_bars) < 2:
            return None

        is_long = position.direction == "LONG"
        closes = np.array([b["close"] for b in recent_bars])

        rsi_period = self.config.get("rsi_period", 14)
        ema_fast_period = self.config.get("ema_fast", 10)   # match analyzer (swing)
        ema_slow_period = self.config.get("ema_slow", 50)   # match analyzer (swing)
        macd_fast = self.config.get("macd_fast", 12)
        macd_slow = self.config.get("macd_slow", 26)
        macd_signal = self.config.get("macd_signal", 9)

        rsi = calc_rsi(closes, rsi_period)
        ema_fast = calc_ema(closes, ema_fast_period)
        ema_slow = calc_ema(closes, ema_slow_period)
        _, _, histogram = calc_macd(closes, macd_fast, macd_slow, macd_signal)

        current_rsi = rsi[-1] if not np.isnan(rsi[-1]) else 50.0
        reversal_signals: list[str] = []
        reversal_score = 0.0

        if is_long:
            # RSI overbought exit
            if current_rsi > self.config.get("rsi_overbought", 70):
                reversal_signals.append(f"RSI overbought ({current_rsi:.0f})")
                reversal_score += 1.0

            # EMA bearish cross
            if (not np.isnan(ema_fast[-1]) and not np.isnan(ema_slow[-1])
                    and not np.isnan(ema_fast[-2]) and not np.isnan(ema_slow[-2])):
                if ema_fast[-1] < ema_slow[-1] and ema_fast[-2] >= ema_slow[-2]:
                    reversal_signals.append("EMA bearish crossover")
                    reversal_score += 1.5
                elif ema_fast[-1] < ema_slow[-1]:
                    reversal_signals.append("Below EMA trend")
                    reversal_score += 0.5

            # MACD bearish flip
            if (not np.isnan(histogram[-1]) and not np.isnan(histogram[-2])):
                if histogram[-1] < 0 and histogram[-2] >= 0:
                    reversal_signals.append("MACD bearish flip")
                    reversal_score += 1.5

        else:  # SHORT
            if current_rsi < self.config.get("rsi_oversold", 30):
                reversal_signals.append(f"RSI oversold ({current_rsi:.0f})")
                reversal_score += 1.0

            if (not np.isnan(ema_fast[-1]) and not np.isnan(ema_slow[-1])
                    and not np.isnan(ema_fast[-2]) and not np.isnan(ema_slow[-2])):
                if ema_fast[-1] > ema_slow[-1] and ema_fast[-2] <= ema_slow[-2]:
                    reversal_signals.append("EMA bullish crossover")
                    reversal_score += 1.5
                elif ema_fast[-1] > ema_slow[-1]:
                    reversal_signals.append("Above EMA trend")
                    reversal_score += 0.5

            if (not np.isnan(histogram[-1]) and not np.isnan(histogram[-2])):
                if histogram[-1] > 0 and histogram[-2] <= 0:
                    reversal_signals.append("MACD bullish flip")
                    reversal_score += 1.5

        if reversal_score == 0:
            return None

        urgency = ExitUrgency.HIGH if reversal_score >= 2.5 else ExitUrgency.MEDIUM

        return ExitSignalResult(
            triggered=True,
            exit_type="indicator_reversal",
            urgency=urgency,
            trigger_price=None,
            current_price=current_bar["close"],
            message=(
                f"INDICATOR REVERSAL on {position.symbol} — "
                f"{', '.join(reversal_signals)}. "
                f"Reversal score: {reversal_score:.1f}/4"
            ),
            details={
                "reversal_signals": reversal_signals,
                "reversal_score": reversal_score,
                "rsi": round(float(current_rsi), 1),
                "ema_fast": round(float(ema_fast[-1]), 2) if not np.isnan(ema_fast[-1]) else None,
                "ema_slow": round(float(ema_slow[-1]), 2) if not np.isnan(ema_slow[-1]) else None,
                "macd_hist": round(float(histogram[-1]), 4) if not np.isnan(histogram[-1]) else None,
            },
        )
