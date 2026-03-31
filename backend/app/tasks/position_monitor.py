"""Position monitor task — runs 3x daily during market days (swing trading)."""

import asyncio
import logging

from app.tasks.celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(name="app.tasks.position_monitor.monitor_positions")
def monitor_positions():
    asyncio.run(_monitor())


async def _monitor():
    from app.db.database import task_session
    from app.engine.data_provider import get_data_provider
    from app.positions.monitor import PositionMonitor

    async with task_session() as db:
        monitor = PositionMonitor(db, get_data_provider())
        alerts = await monitor.check_all_positions()
        await db.commit()

        if alerts:
            logger.info(f"Position monitor: {len(alerts)} exit alerts generated")
