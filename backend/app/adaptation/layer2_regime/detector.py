"""
Layer 2: Regime Detector with parameter application.

Wraps the engine's heuristic regime detector (Phase 1) and will
be upgraded to HMM in production. When a regime change is detected,
it logs the change and applies the appropriate parameter preset.
"""

import logging
from datetime import datetime

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.data_provider import DataProvider
from app.engine.regime import RegimeDetector as BaseRegimeDetector
from app.models.regime_log import RegimeLog
from app.models.parameter_snapshot import ParameterSnapshot
from app.adaptation.layer1_optimizer.parameter_space import clamp_params, validate_weights
from app.adaptation.layer2_regime.presets import get_preset

logger = logging.getLogger(__name__)


class AdaptiveRegimeDetector:
    """
    Detects regime changes and applies parameter presets.

    Flow:
    1. Run base regime detection (heuristic now, HMM later)
    2. Compare against the last logged regime
    3. If changed → log the transition + apply preset overrides
    4. Return the current regime + whether it changed
    """

    def __init__(self, db: AsyncSession, data_provider: DataProvider):
        self.db = db
        self.data = data_provider
        self.base_detector = BaseRegimeDetector(data_provider)

    async def check_regime(self) -> dict:
        """
        Run regime detection. Returns:
        {
            regime, confidence, changed, previous_regime,
            features, preset_applied
        }
        """
        # Detect current regime
        result = await self.base_detector.detect()
        current_regime = result["regime"]
        confidence = result["confidence"]

        # Get previous regime
        prev = await self._get_previous_regime()
        previous_regime = prev.regime if prev else None
        changed = previous_regime is not None and current_regime != previous_regime

        preset_applied = False

        if changed:
            logger.info(
                f"Regime change detected: {previous_regime} → {current_regime} "
                f"(confidence: {confidence:.2f})"
            )

            # Apply preset for new regime
            preset = get_preset(current_regime)
            if preset:
                await self._apply_preset(current_regime, preset)
                preset_applied = True

        # Log the detection (always, for history)
        log_entry = RegimeLog(
            regime=current_regime,
            confidence=confidence,
            previous_regime=previous_regime,
            detection_method=result.get("detection_method", "heuristic"),
            features=result.get("features"),
        )
        self.db.add(log_entry)
        await self.db.flush()

        return {
            "regime": current_regime,
            "confidence": confidence,
            "changed": changed,
            "previous_regime": previous_regime,
            "features": result.get("features"),
            "preset_applied": preset_applied,
        }

    async def _get_previous_regime(self) -> RegimeLog | None:
        result = await self.db.execute(
            select(RegimeLog).order_by(desc(RegimeLog.created_at)).limit(1)
        )
        return result.scalar_one_or_none()

    async def _apply_preset(self, regime: str, preset: dict) -> None:
        """Apply regime preset as a new parameter snapshot."""
        # Get current params as base
        result = await self.db.execute(
            select(ParameterSnapshot).order_by(desc(ParameterSnapshot.created_at)).limit(1)
        )
        current = result.scalar_one_or_none()

        # Merge preset on top of current params
        if current and current.full_config:
            merged = dict(current.full_config)
        else:
            from app.adaptation.layer1_optimizer.parameter_space import get_defaults
            merged = get_defaults()

        merged.update(preset)
        merged = clamp_params(merged)
        merged = validate_weights(merged)

        snapshot = ParameterSnapshot(
            snapshot_type="regime_change",
            trigger=f"regime_{regime}",
            **{k: v for k, v in merged.items() if hasattr(ParameterSnapshot, k)},
            full_config=merged,
        )
        self.db.add(snapshot)
        await self.db.flush()

        logger.info(f"Applied {regime} preset: {preset}")
