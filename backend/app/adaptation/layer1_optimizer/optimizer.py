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
from app.models.signal import Signal
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

    def __init__(self, learning_rate: float = 0.015, decay: float = 0.995, momentum: float = 0.7):
        """
        Args:
            learning_rate: Base learning rate (default 0.015 — conservative online learning).
            decay: Per-trade decay multiplier.
            momentum: EMA momentum for parameter adjustments (0=no momentum, 0.9=heavy smoothing).
        """
        self.learning_rate = learning_rate
        self.decay = decay
        self.momentum = momentum
        self._trade_count = 0
        # Track previous adjustments for momentum smoothing (param_name → last delta)
        self._prev_adjustments: dict[str, float] = {}

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

        # Load linked signal for conviction-weighted learning + component scores
        conviction = 1.0
        signal = None
        if position.entry_signal_id:
            signal = await db.get(Signal, position.entry_signal_id)
            if signal:
                conviction = abs(signal.conviction)

        # Compute parameter adjustments
        adjusted = self._compute_adjustment(current_params, position, pnl, conviction, signal)

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
        self, params: dict, position: Position, pnl: float,
        conviction: float = 1.0, signal: Signal | None = None,
    ) -> dict:
        """
        Nudge parameters based on trade outcome.

        Winners: reinforce the current config slightly
        Losers: push parameters away from current config

        Learning rate is scaled by signal conviction — high-conviction losses
        are stronger learning signals than low-conviction ones.
        """
        adjusted = dict(params)
        lr = self.learning_rate * (self.decay ** self._trade_count)

        # Scale by conviction: high conviction = stronger signal for learning
        lr *= max(conviction, 0.5)

        # Scale adjustment by outcome magnitude (capped at 5% move)
        magnitude = min(abs(pnl) / 100, 0.05)
        direction = 1.0 if pnl > 0 else -1.0

        # Exit parameter adjustments based on how the trade closed
        exit_reason = position.exit_reason or "manual"

        if exit_reason == "stop_loss":
            stop_pct = params.get("default_stop_loss_pct", 5.0)
            if abs(pnl) > stop_pct * 2:
                # Loss far exceeds stop (gap-down) — tighten stops, raise signal bar
                adjusted["atr_stop_multiplier"] = params.get("atr_stop_multiplier", 2.5) - lr * 0.1
                adjusted["default_stop_loss_pct"] = params.get("default_stop_loss_pct", 5.0) - lr * 0.3
                adjusted["min_signal_strength"] = params.get("min_signal_strength", 1.5) + lr * 0.2
            elif pnl < -1.0:
                # Normal stop hit — stop may have been too tight, widen slightly
                adjusted["atr_stop_multiplier"] = params.get("atr_stop_multiplier", 2.5) + lr * 0.1
                adjusted["default_stop_loss_pct"] = params.get("default_stop_loss_pct", 5.0) + lr * 0.2

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

        # Adapt conviction weights based on which component predicted correctly
        adjusted = self._adjust_weights(adjusted, pnl, lr, signal)

        # Apply momentum smoothing — blend new delta with previous delta to
        # reduce parameter whipsaw from noisy single-trade outcomes.
        for name, new_value in list(adjusted.items()):
            if name not in params:
                continue
            new_delta = new_value - params[name]
            if new_delta == 0:
                continue
            prev_delta = self._prev_adjustments.get(name, 0.0)
            smoothed_delta = self.momentum * prev_delta + (1 - self.momentum) * new_delta
            adjusted[name] = params[name] + smoothed_delta
            self._prev_adjustments[name] = smoothed_delta

        # Clamp and normalize
        adjusted = clamp_params(adjusted)
        adjusted = validate_weights(adjusted)

        return adjusted

    def _adjust_weights(
        self, params: dict, pnl: float, lr: float, signal: Signal | None = None,
    ) -> dict:
        """
        Shift conviction weights toward components that predicted correctly.

        Uses the linked signal's tech_score, sentiment_score, fundamental_score
        to identify which component was the strongest contributor.

        Winners: boost the dominant component's weight (it predicted right).
        Losers: reduce the dominant component's weight (it predicted wrong).

        validate_weights() normalizes to sum=1.0 afterward.
        """
        if signal is None:
            return params

        scores = {
            "technical_weight": abs(signal.tech_score),
            "sentiment_weight": abs(signal.sentiment_score),
            "fundamental_weight": abs(signal.fundamental_score),
        }

        # Find which component had the strongest score at entry
        dominant = max(scores, key=scores.get)

        # Small nudge per trade — weights shift gradually
        nudge = lr * 0.02

        if pnl > 0:
            # Winner: boost the dominant component
            params[dominant] = params.get(dominant, 0.3) + nudge
        else:
            # Loser: reduce the dominant component
            params[dominant] = params.get(dominant, 0.3) - nudge

        return params

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
