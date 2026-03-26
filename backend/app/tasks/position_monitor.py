"""Position monitor task — runs every 30 seconds during market hours."""

import asyncio
import logging
from datetime import datetime

import pytz

from app.tasks.celery_app import celery

logger = logging.getLogger(__name__)


def _is_market_hours() -> bool:
    """Check if we're within market hours (9:30 AM - 4:00 PM ET, weekdays)."""
    et = pytz.timezone("America/New_York")
    now = datetime.now(et)
    if now.weekday() >= 5:
        return False
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    return market_open <= now <= market_close


@celery.task(name="app.tasks.position_monitor.monitor_positions")
def monitor_positions():
    if not _is_market_hours():
        return
    asyncio.run(_monitor())


async def _monitor():
    from app.db.database import async_session
    from app.engine.data_provider import get_data_provider
    from app.positions.monitor import PositionMonitor

    async with async_session() as db:
        monitor = PositionMonitor(db, get_data_provider())
        alerts = await monitor.check_all_positions()
        await db.commit()

        if alerts:
            logger.info(f"Position monitor: {len(alerts)} exit alerts generated")
