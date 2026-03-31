"""
Time-Based Exit Strategy (Swing Trading).

Max Hold Time: Fires when position held for N trading days (default 25).
If a swing trade hasn't worked in ~5 weeks, the thesis is probably wrong.

EOD exit logic is disabled by default for swing trading — holding overnight
is expected behavior.
"""

from datetime import datetime

from app.models.position import Position
from app.positions.exit_strategies.base import ExitStrategy, ExitSignalResult, ExitUrgency


class TimeBasedExitStrategy(ExitStrategy):
    async def evaluate(
        self, position: Position, current_bar: dict, recent_bars: list[dict]
    ) -> ExitSignalResult | None:
        return self._check_max_hold(position, current_bar)

    def _check_max_hold(
        self, position: Position, current_bar: dict
    ) -> ExitSignalResult | None:
        days_held = position.bars_held or 0
        max_days = position.max_hold_days  # interpreted as days for swing trading

        if max_days and days_held >= max_days:
            return ExitSignalResult(
                triggered=True,
                exit_type="max_hold_warning",
                urgency=ExitUrgency.MEDIUM,
                trigger_price=None,
                current_price=current_bar["close"],
                message=(
                    f"MAX HOLD TIME reached on {position.symbol} — "
                    f"Open for {days_held} trading days. "
                    f"Original thesis may no longer apply."
                ),
                details={
                    "days_held": days_held,
                    "max_days": max_days,
                },
            )
        return None
