"""
Adaptation Coordinator — orchestrates all 3 layers.

Layer 1 (Optimizer):  After each closed trade
Layer 2 (Regime):     Every 30 minutes during market hours
Layer 3 (Meta):       Once daily at 4:15 PM ET

This module provides the entry points that Celery tasks call.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.data_provider import DataProvider
from app.models.position import Position
from app.adaptation.layer1_optimizer.optimizer import OnlineOptimizer
from app.adaptation.layer2_regime.detector import AdaptiveRegimeDetector
from app.adaptation.layer3_meta.analyst import MetaAnalyst

logger = logging.getLogger(__name__)

# Singleton optimizer (maintains trade count across calls)
_optimizer = OnlineOptimizer()


async def on_trade_closed(db: AsyncSession, position: Position) -> dict:
    """
    Called after a position is closed.
    Triggers Layer 1 optimizer update.
    """
    snapshot = await _optimizer.update_after_trade(db, position)
    return {
        "optimized": snapshot is not None,
        "snapshot_id": snapshot.id if snapshot else None,
    }


async def on_regime_check(db: AsyncSession, data_provider: DataProvider) -> dict:
    """
    Called every 30 minutes during market hours.
    Triggers Layer 2 regime detection.
    """
    detector = AdaptiveRegimeDetector(db, data_provider)
    result = await detector.check_regime()
    return result


async def on_daily_review(db: AsyncSession) -> dict:
    """
    Called at 4:15 PM ET daily.
    Triggers Layer 3 Claude meta-review.
    """
    analyst = MetaAnalyst(db)
    review = await analyst.run_daily_review()
    return {
        "review_id": review.id,
        "summary": review.summary,
        "recommendations": review.recommendations,
    }
