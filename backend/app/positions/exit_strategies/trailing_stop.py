"""
Trailing Stop Exit Strategy.

Moves the stop up as price advances, locking in profits.
Uses ATR-based trailing distance: stop = highest_close - trail_atr_multiplier * ATR.

Only activates after the position is in profit by at least `activation_pct`.
Once active, the trailing stop only moves UP (for longs) or DOWN (for shorts).

Triggers CRITICAL when the trailing stop is breached.
Triggers MEDIUM when price pulls back 50%+ from its high since activation.
"""

import numpy as np

from app.engine.indicators import calc_atr
from app.models.position import Position
from app.positions.exit_strategies.base import ExitStrategy, ExitSignalResult, ExitUrgency


class TrailingStopStrategy(ExitStrategy):
    def __init__(self, trail_atr_multiplier: float = 2.0, activation_pct: float = 1.5):
        """
        Args:
            trail_atr_multiplier: Trail distance as multiple of ATR (default 2.0)
            activation_pct: Minimum profit % before trailing stop activates (default 1.5%)
        """
        self.trail_atr_multiplier = trail_atr_multiplier
        self.activation_pct = activation_pct

    async def evaluate(
        self, position: Position, current_bar: dict, recent_bars: list[dict]
    ) -> ExitSignalResult | None:
        if len(recent_bars) < 15:
            return None

        price = current_bar["close"]
        entry = position.entry_price
        is_long = position.direction == "LONG"

        # Calculate current profit %
        if is_long:
            profit_pct = (price - entry) / entry * 100
        else:
            profit_pct = (entry - price) / entry * 100

        # Only activate after position is in profit by activation_pct
        if profit_pct < self.activation_pct:
            return None

        # Calculate ATR for trail distance
        highs = np.array([b["high"] for b in recent_bars])
        lows = np.array([b["low"] for b in recent_bars])
        closes = np.array([b["close"] for b in recent_bars])
        atr = calc_atr(highs, lows, closes)
        current_atr = atr[-1] if not np.isnan(atr[-1]) else price * 0.02

        trail_distance = current_atr * self.trail_atr_multiplier

        # Compute trailing stop from highest/lowest price since entry
        if is_long:
            high_water = position.high_since_entry or price
            trail_stop = high_water - trail_distance
            # Trail stop must be above entry (we're in profit)
            trail_stop = max(trail_stop, entry)
            worst_price = current_bar.get("low", price)
            triggered = worst_price <= trail_stop
            pullback_pct = (high_water - price) / (high_water - entry) * 100 if high_water > entry else 0
        else:
            low_water = position.low_since_entry or price
            trail_stop = low_water + trail_distance
            trail_stop = min(trail_stop, entry)
            worst_price = current_bar.get("high", price)
            triggered = worst_price >= trail_stop
            pullback_pct = (price - low_water) / (entry - low_water) * 100 if entry > low_water else 0

        if triggered:
            locked_pct = (trail_stop - entry) / entry * 100 if is_long else (entry - trail_stop) / entry * 100
            return ExitSignalResult(
                triggered=True,
                exit_type="trailing_stop",
                urgency=ExitUrgency.CRITICAL,
                trigger_price=round(trail_stop, 2),
                current_price=price,
                message=(
                    f"TRAILING STOP HIT on {position.symbol} — "
                    f"Price ${price:.2f} breached trail at ${trail_stop:.2f} "
                    f"(locked in {locked_pct:+.2f}%). Exit to protect gains."
                ),
                details={
                    "trail_stop": round(trail_stop, 2),
                    "high_water": round(position.high_since_entry or price, 2),
                    "atr": round(float(current_atr), 4),
                    "trail_multiplier": self.trail_atr_multiplier,
                    "locked_pct": round(locked_pct, 2),
                },
            )

        # Warning: significant pullback from high (>50% of gains given back)
        if pullback_pct > 50:
            return ExitSignalResult(
                triggered=True,
                exit_type="trailing_stop",
                urgency=ExitUrgency.MEDIUM,
                trigger_price=round(trail_stop, 2),
                current_price=price,
                message=(
                    f"WARNING: {position.symbol} pulled back {pullback_pct:.0f}% from peak — "
                    f"trailing stop at ${trail_stop:.2f}"
                ),
                details={
                    "pullback_pct": round(pullback_pct, 1),
                    "trail_stop": round(trail_stop, 2),
                },
            )

        return None
