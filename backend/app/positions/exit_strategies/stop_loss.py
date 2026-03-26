"""
Stop Loss Exit Strategy.

Triggers CRITICAL urgency when price breaches the stop level.
Also fires MEDIUM warning when price is within 30% of the stop.

Uses the TIGHTEST of all configured stops (fixed price, percentage, ATR-based).
"""

from app.models.position import Position
from app.positions.exit_strategies.base import ExitStrategy, ExitSignalResult, ExitUrgency


class StopLossStrategy(ExitStrategy):
    async def evaluate(
        self, position: Position, current_bar: dict, recent_bars: list[dict]
    ) -> ExitSignalResult | None:
        price = current_bar["close"]
        entry = position.entry_price
        is_long = position.direction == "LONG"

        # Collect all configured stop levels
        stops: list[float] = []

        if position.stop_loss_price:
            stops.append(position.stop_loss_price)

        if position.stop_loss_pct:
            if is_long:
                stops.append(entry * (1 - position.stop_loss_pct / 100))
            else:
                stops.append(entry * (1 + position.stop_loss_pct / 100))

        if not stops:
            return None

        # Use tightest stop
        if is_long:
            stop_level = max(stops)  # Highest stop = tightest for long
            triggered = price <= stop_level
        else:
            stop_level = min(stops)  # Lowest stop = tightest for short
            triggered = price >= stop_level

        if triggered:
            loss_pct = abs(price - entry) / entry * 100
            return ExitSignalResult(
                triggered=True,
                exit_type="stop_loss",
                urgency=ExitUrgency.CRITICAL,
                trigger_price=stop_level,
                current_price=price,
                message=(
                    f"STOP LOSS HIT on {position.symbol} — "
                    f"Price ${price:.2f} breached stop at ${stop_level:.2f} "
                    f"(loss: {loss_pct:.2f}%). Exit immediately."
                ),
                details={
                    "stop_level": round(stop_level, 2),
                    "entry_price": entry,
                    "loss_pct": round(loss_pct, 2),
                },
            )

        # Warning if approaching stop (within 30% of distance)
        if is_long:
            distance = price - stop_level
            total_distance = entry - stop_level
        else:
            distance = stop_level - price
            total_distance = stop_level - entry

        if total_distance > 0 and distance / total_distance < 0.3:
            return ExitSignalResult(
                triggered=True,
                exit_type="stop_loss",
                urgency=ExitUrgency.MEDIUM,
                trigger_price=stop_level,
                current_price=price,
                message=(
                    f"WARNING: {position.symbol} approaching stop loss — "
                    f"Price ${price:.2f}, stop at ${stop_level:.2f}"
                ),
                details={
                    "distance_remaining_pct": round(distance / total_distance * 100, 1),
                },
            )

        return None
