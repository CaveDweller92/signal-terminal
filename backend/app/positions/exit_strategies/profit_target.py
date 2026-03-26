"""
Profit Target Exit Strategy.

Triggers HIGH urgency when price hits the target level.
Also fires LOW alerts at 75% of target as informational.
"""

from app.models.position import Position
from app.positions.exit_strategies.base import ExitStrategy, ExitSignalResult, ExitUrgency


class ProfitTargetStrategy(ExitStrategy):
    async def evaluate(
        self, position: Position, current_bar: dict, recent_bars: list[dict]
    ) -> ExitSignalResult | None:
        price = current_bar["close"]
        entry = position.entry_price
        is_long = position.direction == "LONG"

        targets: list[float] = []
        if position.profit_target_price:
            targets.append(position.profit_target_price)
        if position.profit_target_pct:
            if is_long:
                targets.append(entry * (1 + position.profit_target_pct / 100))
            else:
                targets.append(entry * (1 - position.profit_target_pct / 100))

        if not targets:
            return None

        if is_long:
            target_level = min(targets)  # Conservative target for long
            triggered = price >= target_level
            gain_pct = (price - entry) / entry * 100
        else:
            target_level = max(targets)
            triggered = price <= target_level
            gain_pct = (entry - price) / entry * 100

        if triggered:
            return ExitSignalResult(
                triggered=True,
                exit_type="profit_target",
                urgency=ExitUrgency.HIGH,
                trigger_price=target_level,
                current_price=price,
                message=(
                    f"TARGET HIT on {position.symbol} — "
                    f"Price ${price:.2f} reached target ${target_level:.2f} "
                    f"(gain: +{gain_pct:.2f}%). Consider taking profits."
                ),
                details={
                    "target_level": round(target_level, 2),
                    "gain_pct": round(gain_pct, 2),
                    "risk_reward_achieved": round(
                        gain_pct / position.stop_loss_pct if position.stop_loss_pct else 0, 2
                    ),
                },
            )

        # Partial target alert (75%)
        total_distance = abs(target_level - entry)
        current_distance = abs(price - entry)
        if total_distance > 0:
            progress = current_distance / total_distance
            if progress >= 0.75 and gain_pct > 0:
                return ExitSignalResult(
                    triggered=True,
                    exit_type="profit_target",
                    urgency=ExitUrgency.LOW,
                    trigger_price=target_level,
                    current_price=price,
                    message=(
                        f"{position.symbol} at 75% of profit target — "
                        f"+{gain_pct:.2f}% (target: ${target_level:.2f})"
                    ),
                    details={"progress_pct": 75, "gain_pct": round(gain_pct, 2)},
                )

        return None
