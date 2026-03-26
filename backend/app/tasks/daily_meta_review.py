"""Daily meta-review task — runs at 4:15 PM ET weekdays."""

import asyncio
import logging

from app.tasks.celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(name="app.tasks.daily_meta_review.run_daily_meta_review")
def run_daily_meta_review():
    asyncio.run(_review())


async def _review():
    from app.db.database import async_session
    from app.adaptation import on_daily_review

    async with async_session() as db:
        result = await on_daily_review(db)
        await db.commit()
        logger.info(f"Daily meta-review complete: {result['summary'][:100]}")
