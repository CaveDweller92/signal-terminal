"""Weekly universe update — runs Sunday 3:00 AM ET."""

import asyncio
import logging

from app.tasks.celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(name="app.tasks.universe_update.refresh_all_universes")
def refresh_all_universes():
    asyncio.run(_refresh())


async def _refresh():
    from app.db.database import task_session
    from app.discovery.universe import seed_universe

    async with task_session() as db:
        counts = await seed_universe(db)
        await db.commit()
        total = sum(counts.values())
        logger.info(f"Universe refreshed: {total} stocks ({counts})")
