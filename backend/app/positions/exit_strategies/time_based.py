"""
Time-Based Exit Strategy.

Two conditions:
1. EOD Warning: Fires 15 min before market close (3:45 PM ET)
   HIGH at 15 min, CRITICAL at 5 min. Avoids overnight risk.

2. Max Hold Time: Fires when position held for N bars (default 60 = 5 hours).
   If a trade hasn't worked in 5 hours, the thesis is probably wrong.
"""

from datetime import datetime, time

import pytz

from app.models.position import Position
from app.positions.exit_strategies.base import ExitStrategy, ExitSignalResult, ExitUrgency


class TimeBasedExitStrategy(ExitStrategy):
    def __init__(
        self,
        timezone: str = "America/New_York",
        eod_warning_minutes: int = 15,
    ):
        self.tz = pytz.timezone(timezone)
        self.eod_warning_minutes = eod_warning_minutes

    async def evaluate(
        self, position: Position, current_bar: dict, recent_bars: list[dict]
    ) -> ExitSignalResult | None:
        now = datetime.now(self.tz)

        # Only check EOD on weekdays during market hours
        if now.weekday() >= 5:
            return self._check_max_hold(position, current_bar)

        close_time = now.replace(hour=16, minute=0, second=0, microsecond=0)
        minutes_to_close = (close_time - now).total_seconds() / 60

        # EOD Warning
        if position.eod_exit_enabled and 0 < minutes_to_close <= self.eod_warning_minutes:
            urgency = ExitUrgency.CRITICAL if minutes_to_close <= 5 else ExitUrgency.HIGH
            pnl_pct = position.unrealized_pnl_pct or 0

            return ExitSignalResult(
                triggered=True,
                exit_type="eod_warning",
                urgency=urgency,
                trigger_price=None,
                current_price=current_bar["close"],
                message=(
                    f"EOD EXIT WARNING — {position.symbol} still open, "
                    f"{minutes_to_close:.0f} min to close. "
                    f"Current P&L: {pnl_pct:+.2f}%. "
                    f"{'Close to avoid overnight risk.' if urgency == ExitUrgency.CRITICAL else 'Consider closing.'}"
                ),
                details={
                    "minutes_to_close": round(minutes_to_close),
                    "current_pnl_pct": round(pnl_pct, 2),
                },
            )

        # Max hold time
        return self._check_max_hold(position, current_bar)

    def _check_max_hold(
        self, position: Position, current_bar: dict
    ) -> ExitSignalResult | None:
        if position.max_hold_bars and position.bars_held >= position.max_hold_bars:
            return ExitSignalResult(
                triggered=True,
                exit_type="max_hold_warning",
                urgency=ExitUrgency.MEDIUM,
                trigger_price=None,
                current_price=current_bar["close"],
                message=(
                    f"MAX HOLD TIME reached on {position.symbol} — "
                    f"Open for {position.bars_held} bars ({position.bars_held * 5} min). "
                    f"Original thesis may no longer apply."
                ),
                details={
                    "bars_held": position.bars_held,
                    "max_bars": position.max_hold_bars,
                    "minutes_held": position.bars_held * 5,
                },
            )
        return None
