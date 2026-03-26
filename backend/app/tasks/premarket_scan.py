"""Pre-market scan task — runs at 5:00 AM ET weekdays."""

import asyncio
import logging

from app.tasks.celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(name="app.tasks.premarket_scan.run_scan")
def run_scan():
    asyncio.run(_run_scan())


async def _run_scan():
    from app.db.database import async_session
    from app.engine.data_provider import get_data_provider
    from app.discovery.universe import get_active_symbols
    from app.discovery.screener import PremarketScreener

    async with async_session() as db:
        stocks = await get_active_symbols(db)
        if not stocks:
            logger.warning("No stocks in universe — skipping scan")
            return

        provider = get_data_provider()
        screener = PremarketScreener(provider)
        results = await screener.scan(stocks, db)
        await db.commit()
        logger.info(f"Pre-market scan complete: {len(results)} stocks scored")
