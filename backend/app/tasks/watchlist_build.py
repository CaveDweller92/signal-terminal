"""Watchlist build task — runs at 6:00 AM ET weekdays."""

import asyncio
import logging

from app.tasks.celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(name="app.tasks.watchlist_build.build_daily_watchlist")
def build_daily_watchlist():
    asyncio.run(_build_watchlist())


async def _build_watchlist():
    from app.db.database import async_session
    from app.engine.data_provider import get_data_provider
    from app.engine.regime import RegimeDetector
    from app.discovery.ai_watchlist import build_watchlist

    async with async_session() as db:
        provider = get_data_provider()
        detector = RegimeDetector(provider)
        regime_result = await detector.detect()

        watchlist = await build_watchlist(db, regime=regime_result["regime"])
        await db.commit()
        logger.info(f"Watchlist built: {len(watchlist)} picks")
