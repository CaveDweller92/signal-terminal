"""
Live Scanner — background coroutine that runs inside the FastAPI process.

Two loops:
  - Every 30 seconds: check all open positions for exit signals, broadcast via WS
  - Every 5 minutes during market hours: re-analyze the watchlist, broadcast via WS

Runs as an asyncio.Task started in main.py startup_event.
Uses the ws_manager singleton directly (no Celery/pub-sub needed).
"""

import asyncio
import logging
from datetime import datetime, date, time

from sqlalchemy import select

from app.api.websocket import ws_manager
from app.db.database import async_session
from app.engine.analyzer import SignalAnalyzer
from app.engine.data_provider import get_data_provider
from app.models.watchlist import DailyWatchlist
from app.models.screener_result import ScreenerResult
from app.positions.monitor import PositionMonitor

logger = logging.getLogger(__name__)

# Market hours (Eastern — server must run with TZ=America/New_York or UTC is fine for simulation)
_MARKET_OPEN = time(9, 30)
_MARKET_CLOSE = time(16, 15)

# Intervals
_POSITION_CHECK_INTERVAL = 30      # seconds
_SIGNAL_SCAN_INTERVAL = 5 * 60    # seconds (5 minutes)


def _is_market_hours() -> bool:
    """True during approximate market hours (Mon–Fri, 9:30–16:15 ET)."""
    now = datetime.now()
    if now.weekday() >= 5:  # Saturday / Sunday
        return False
    t = now.time()
    return _MARKET_OPEN <= t <= _MARKET_CLOSE


async def _get_scan_symbols() -> list[str]:
    """
    Resolve the symbols to scan in priority order:
      1. Today's DailyWatchlist (Claude-curated or screener-selected)
      2. Top 12 most recent ScreenerResult records
    """
    async with async_session() as session:
        # 1. Today's watchlist
        today = date.today()
        result = await session.execute(
            select(DailyWatchlist.symbol)
            .where(DailyWatchlist.watch_date == today)
            .where(DailyWatchlist.user_removed == False)
            .order_by(DailyWatchlist.screener_rank)
        )
        symbols = [row[0] for row in result.fetchall()]
        if symbols:
            logger.debug(f"LiveScanner: using today's watchlist ({len(symbols)} symbols)")
            return symbols

        # 2. Most recent screener results
        result = await session.execute(
            select(ScreenerResult.symbol)
            .order_by(ScreenerResult.composite_score.desc())
            .limit(12)
        )
        symbols = [row[0] for row in result.fetchall()]
        if symbols:
            logger.debug(f"LiveScanner: using screener results ({len(symbols)} symbols)")
            return symbols

    logger.debug("LiveScanner: no symbols available — run the screener first")
    return []


async def _scan_signals() -> None:
    """Resolve watchlist symbols, analyze each, broadcast signal_update."""
    try:
        symbols = await _get_scan_symbols()
        if not symbols:
            return
        provider = get_data_provider()
        analyzer = SignalAnalyzer(provider)
        results = []
        for symbol in symbols:
            signal = await analyzer.analyze(symbol)
            if signal is not None:
                results.append(signal)
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

    Position checks run every 30 s.
    Signal scans run every 5 min, but only during market hours.
    """
    logger.info("LiveScanner: started")
    last_signal_scan = 0.0  # epoch seconds of last scan

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
            await asyncio.sleep(5)  # brief back-off before retrying
