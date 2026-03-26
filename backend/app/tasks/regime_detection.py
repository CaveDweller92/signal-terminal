"""Regime detection task — runs every 30 min during market hours."""

import asyncio
import logging

from app.tasks.celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(name="app.tasks.regime_detection.run_regime_detection")
def run_regime_detection():
    asyncio.run(_detect())


async def _detect():
    from app.db.database import async_session
    from app.engine.data_provider import get_data_provider
    from app.adaptation import on_regime_check

    async with async_session() as db:
        result = await on_regime_check(db, get_data_provider())
        await db.commit()

        if result.get("changed"):
            logger.info(
                f"Regime changed: {result['previous_regime']} → {result['regime']} "
                f"(confidence: {result['confidence']:.2f})"
            )
