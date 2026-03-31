"""
Composite Exit Engine.

Runs all exit strategies in parallel on a position,
deduplicates alerts (cooldown per exit_type), and ranks by urgency.
"""

import logging
from datetime import datetime

from app.models.position import Position
from app.positions.exit_strategies.base import ExitStrategy, ExitSignalResult, ExitUrgency

logger = logging.getLogger(__name__)


class CompositeExitStrategy:
    def __init__(self, strategies: list[ExitStrategy], cooldown_minutes: int = 1440):
        self.strategies = strategies
        self.cooldown_minutes = cooldown_minutes
        self._recent_alerts: dict[tuple[int, str], datetime] = {}

    async def evaluate_all(
        self, position: Position, current_bar: dict, recent_bars: list[dict]
    ) -> list[ExitSignalResult]:
        """Run all strategies, return triggered signals sorted by urgency."""
        results: list[ExitSignalResult] = []

        for strategy in self.strategies:
            try:
                result = await strategy.evaluate(position, current_bar, recent_bars)
                if result and result.triggered:
                    # Check cooldown — don't spam the same alert type
                    key = (position.id, result.exit_type)
                    last_fired = self._recent_alerts.get(key)
                    if last_fired:
                        elapsed = (datetime.utcnow() - last_fired).total_seconds() / 60
                        # Always allow CRITICAL through, cooldown for others
                        if elapsed < self.cooldown_minutes and result.urgency != ExitUrgency.CRITICAL:
                            continue

                    self._recent_alerts[key] = datetime.utcnow()
                    results.append(result)

            except Exception as e:
                logger.error(f"Exit strategy error for {position.symbol}: {e}")

        # Sort by urgency priority
        urgency_order = {
            ExitUrgency.CRITICAL: 0,
            ExitUrgency.HIGH: 1,
            ExitUrgency.MEDIUM: 2,
            ExitUrgency.LOW: 3,
        }
        results.sort(key=lambda r: urgency_order[r.urgency])

        return results
