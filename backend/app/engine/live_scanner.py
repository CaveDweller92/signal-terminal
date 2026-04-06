"""
Live Scanner — background coroutine that runs inside the FastAPI process.

Swing trading mode:
  - Every 30 minutes: check all open positions for exit signals, broadcast via WS
  - Every 60 minutes during market hours: re-analyze the watchlist, broadcast via WS

Runs as an asyncio.Task started in main.py startup_event.
Uses the ws_manager singleton directly (no Celery/pub-sub needed).
"""

import asyncio
import logging
from datetime import datetime, date, time

from sqlalchemy import select

from app.api.websocket import ws_manager
from app.db.database import async_session
from app.engine.data_provider import get_data_provider
from app.engine.signal_service import SignalService
from app.models.watchlist import DailyWatchlist
from app.models.screener_result import ScreenerResult
from app.positions.monitor import PositionMonitor

logger = logging.getLogger(__name__)

# Market hours (Eastern)
_MARKET_OPEN = time(9, 30)
_MARKET_CLOSE = time(16, 15)

# Intervals (swing trading — much less frequent than day trading)
_POSITION_CHECK_INTERVAL = 30 * 60   # 30 minutes
_SIGNAL_SCAN_INTERVAL = 60 * 60      # 60 minutes


def _is_market_hours() -> bool:
    """True during approximate market hours (Mon-Fri, 9:30-16:15 ET)."""
    now = datetime.now()
    if now.weekday() >= 5:
        return False
    t = now.time()
    return _MARKET_OPEN <= t <= _MARKET_CLOSE


async def _get_scan_symbols() -> list[str]:
    """
    Resolve the symbols to scan in priority order:
      1. Today's DailyWatchlist (Claude-curated or screener-selected)
      2. Top N most recent ScreenerResult records (N = watchlist_size)

    Always includes symbols from open positions.
    """
    from app.config import settings
    from app.models.position import Position

    async with async_session() as session:
        today = date.today()
        result = await session.execute(
            select(DailyWatchlist.symbol)
            .where(DailyWatchlist.watch_date == today)
            .where(DailyWatchlist.user_removed == False)
            .order_by(DailyWatchlist.screener_rank)
        )
        symbols = [row[0] for row in result.fetchall()]

        if not symbols:
            result = await session.execute(
                select(ScreenerResult.symbol)
                .order_by(ScreenerResult.composite_score.desc())
                .limit(settings.watchlist_size)
            )
            symbols = [row[0] for row in result.fetchall()]

        # Always include open position symbols ON TOP of the full watchlist
        pos_result = await session.execute(
            select(Position.symbol).where(Position.status == "OPEN")
        )
        position_symbols = [row[0] for row in pos_result.fetchall()]

        # Watchlist first (full size), then add positions not already in it
        seen = set()
        merged: list[str] = []
        for sym in symbols:
            if sym not in seen:
                seen.add(sym)
                merged.append(sym)
        for sym in position_symbols:
            if sym not in seen:
                seen.add(sym)
                merged.append(sym)

        if merged:
            logger.debug(f"LiveScanner: scanning {len(merged)} symbols ({len(position_symbols)} positions + {len(symbols)} watchlist)")

        return merged

    logger.debug("LiveScanner: no symbols available — run the screener first")
    return []


async def _scan_signals() -> None:
    """Resolve watchlist symbols, analyze each, persist to DB, broadcast signal_update."""
    try:
        symbols = await _get_scan_symbols()
        if not symbols:
            return
        provider = get_data_provider()
        async with async_session() as session:
            service = SignalService(session, provider)
            results = await service.analyze_batch(symbols)
            await session.commit()
        results.sort(key=lambda s: abs(s["conviction"]), reverse=True)

        await ws_manager.broadcast({
            "type": "signal_update",
            "signals": results,
            "count": len(results),
            "timestamp": datetime.utcnow().isoformat(),
        })
        logger.info(f"LiveScanner: broadcast {len(results)} signals")
    except Exception as e:
        logger.error(f"LiveScanner: signal scan error: {e}")


async def _check_positions() -> None:
    """Check all open positions and broadcast any exit alerts."""
    try:
        async with async_session() as session:
            provider = get_data_provider()
            monitor = PositionMonitor(session, provider)
            alerts = await monitor.check_all_positions()
            await session.commit()

        for alert in alerts:
            await ws_manager.broadcast(alert)

        if alerts:
            logger.info(f"LiveScanner: broadcast {len(alerts)} exit alert(s)")
    except Exception as e:
        logger.error(f"LiveScanner: position check error: {e}")


async def run_live_scanner() -> None:
    """
    Main background loop. Runs forever until the task is cancelled.

    Position checks run every 30 min.
    Signal scans run every 60 min during market hours.
    """
    logger.info("LiveScanner: started (swing trading mode)")
    last_signal_scan = 0.0

    while True:
        try:
            await asyncio.sleep(_POSITION_CHECK_INTERVAL)

            await _check_positions()

            now = asyncio.get_event_loop().time()
            if _is_market_hours() and (now - last_signal_scan) >= _SIGNAL_SCAN_INTERVAL:
                await _scan_signals()
                last_signal_scan = now

        except asyncio.CancelledError:
            logger.info("LiveScanner: cancelled, shutting down")
            break
        except Exception as e:
            logger.error(f"LiveScanner: unexpected error: {e}")
            await asyncio.sleep(5)
