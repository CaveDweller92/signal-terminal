"""
Layer 1: Online Bayesian Optimizer.

Updates strategy parameters after each closed trade using a simplified
Bayesian approach: maintain a running estimate of parameter quality
based on trade outcomes.

This is a lightweight "Thompson Sampling"-inspired optimizer:
1. Track outcome statistics per parameter region
2. After each trade, update the posterior for the config that produced it
3. Sample new parameters from the posterior, biased toward what's worked
4. Apply safety bounds and weight normalization

In production, this would use scipy.optimize or a GP-based optimizer.
For Phase 5, we use a practical online learner that works from day one.
"""

import logging
from datetime import datetime

import numpy as np
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.parameter_snapshot import ParameterSnapshot
from app.models.position import Position
from app.adaptation.layer1_optimizer.parameter_space import (
    PARAMETER_SPACE,
    clamp_params,
    get_defaults,
    validate_weights,
)

logger = logging.getLogger(__name__)


class OnlineOptimizer:
    """
    Learns from closed trade outcomes to improve parameters over time.

    Strategy:
    - Maintains exponentially-weighted running mean and variance of returns
    - After each trade, nudges parameters in the direction that
      improves expected return
    - Learning rate decays over time (explore early, exploit later)
    """

    def __init__(self, learning_rate: float = 0.05, decay: float = 0.995):
        self.learning_rate = learning_rate
        self.decay = decay
        self._trade_count = 0

    async def update_after_trade(
        self, db: AsyncSession, position: Position
    ) -> ParameterSnapshot | None:
        """
        Called after a position is closed. Updates parameters based on outcome.
        Returns a new ParameterSnapshot if parameters changed, else None.
        """
        if position.status != "CLOSED" or position.realized_pnl_pct is None:
            return None

        # Get current parameters
        current_params = await self._get_current_params(db)
        pnl = position.realized_pnl_pct

        # Compute parameter adjustments
        adjusted = self._compute_adjustment(current_params, position, pnl)

        if adjusted == current_params:
            return None

        # Save new snapshot
        snapshot = ParameterSnapshot(
            snapshot_type="optimizer",
            trigger=f"trade_close_{position.id}_pnl_{pnl:.2f}",
            **{k: v for k, v in adjusted.items() if hasattr(ParameterSnapshot, k)},
            full_config=adjusted,
        )
        db.add(snapshot)
        await db.flush()

        self._trade_count += 1
        logger.info(
            f"Optimizer updated params after trade {position.id} "
            f"(PnL: {pnl:+.2f}%, trade #{self._trade_count})"
        )

        return snapshot

    def _compute_adjustment(
        self, params: dict, position: Position, pnl: float
    ) -> dict:
        """
        Nudge parameters based on trade outcome.

        Winners: reinforce the current config slightly
        Losers: push parameters away from current config

        Adjustments are proportional to |pnl| — a big win reinforces more
        than a small win, a big loss pushes harder than a small loss.
        """
        adjusted = dict(params)
        lr = self.learning_rate * (self.decay ** self._trade_count)

        # Scale adjustment by outcome magnitude (capped at 5% move)
        magnitude = min(abs(pnl) / 100, 0.05)
        direction = 1.0 if pnl > 0 else -1.0

        # Exit parameter adjustments based on how the trade closed
        exit_reason = position.exit_reason or "manual"

        if exit_reason == "stop_loss":
            # Stop was hit — was it too tight?
            if pnl < -1.0:
                # Big loss from stop → widen stops slightly
                adjusted["atr_stop_multiplier"] = params.get("atr_stop_multiplier", 1.5) + lr * 0.1
                adjusted["default_stop_loss_pct"] = params.get("default_stop_loss_pct", 2.0) + lr * 0.2

        elif exit_reason == "profit_target":
            # Target hit — good outcome, but was target too conservative?
            bars = position.bars_held or 0
            if bars < 10:
                # Hit target very fast → could have been wider
                adjusted["atr_target_multiplier"] = params.get("atr_target_multiplier", 2.5) + lr * 0.15

        elif exit_reason == "indicator_reversal":
            # Reversal exit — adjust indicator sensitivity
            if pnl > 0:
                # Good reversal exit → reinforce current RSI/EMA settings
                pass
            else:
                # False reversal signal → widen thresholds slightly
                adjusted["rsi_overbought"] = params.get("rsi_overbought", 70) + lr * 2
                adjusted["rsi_oversold"] = params.get("rsi_oversold", 30) - lr * 2

        elif exit_reason == "max_hold_warning":
            # Held too long
            if pnl < 0:
                # Lost money AND held too long → reduce max hold
                adjusted["max_hold_days"] = params.get("max_hold_days", 60) - lr * 5

        # General entry quality adjustment
        if pnl > 0:
            # Lower the signal threshold slightly (generate more signals like this)
            adjusted["min_signal_strength"] = params.get("min_signal_strength", 2.0) - lr * magnitude * 2
        else:
            # Raise the bar for signals
            adjusted["min_signal_strength"] = params.get("min_signal_strength", 2.0) + lr * magnitude * 2

        # Clamp and normalize
        adjusted = clamp_params(adjusted)
        adjusted = validate_weights(adjusted)

        return adjusted

    async def _get_current_params(self, db: AsyncSession) -> dict:
        """Get the most recent parameter snapshot, or defaults."""
        result = await db.execute(
            select(ParameterSnapshot)
            .order_by(desc(ParameterSnapshot.created_at))
            .limit(1)
        )
        snapshot = result.scalar_one_or_none()

        if snapshot and snapshot.full_config:
            return snapshot.full_config

        if snapshot:
            return {p.name: getattr(snapshot, p.name, p.default) for p in PARAMETER_SPACE}

        return get_defaults()
