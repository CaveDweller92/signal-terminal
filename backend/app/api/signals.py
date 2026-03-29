"""
Signal API routes.

GET /api/signals           — analyze today's watchlist symbols, return signals
GET /api/signals/{symbol}  — analyze a single symbol
"""

from datetime import date

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.db.database import async_session
from app.engine.analyzer import SignalAnalyzer
from app.engine.data_provider import get_data_provider
from app.models.screener_result import ScreenerResult
from app.models.watchlist import DailyWatchlist

router = APIRouter(prefix="/api/signals", tags=["signals"])


async def _resolve_symbols() -> list[str]:
    """
    Resolve symbols to scan in priority order:
      1. Today's DailyWatchlist
      2. Top 12 most recent ScreenerResult records
      3. Empty list (no hardcoded fallback)
    """
    async with async_session() as session:
        today = date.today()
        result = await session.execute(
            select(DailyWatchlist.symbol)
            .where(DailyWatchlist.watch_date == today)
            .where(DailyWatchlist.user_removed == False)
            .order_by(DailyWatchlist.screener_rank)
        )
        symbols = [row[0] for row in result.fetchall()]
        if symbols:
            return symbols

        result = await session.execute(
            select(ScreenerResult.symbol)
            .order_by(ScreenerResult.composite_score.desc())
            .limit(12)
        )
        return [row[0] for row in result.fetchall()]


@router.get("")
async def get_signals(
    symbols: str | None = Query(
        None,
        description="Comma-separated symbols. Defaults to today's watchlist.",
    ),
):
    """
    Analyze multiple symbols and return their signals.

    Returns a list of signal objects sorted by absolute conviction
    (strongest signals first).
    """
    if symbols:
        symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    else:
        symbol_list = await _resolve_symbols()

    if not symbol_list:
        return {"signals": [], "count": 0, "message": "No watchlist yet — run the screener first."}

    provider = get_data_provider()
    analyzer = SignalAnalyzer(provider)

    results = []
    for symbol in symbol_list:
        signal = await analyzer.analyze(symbol)
        if signal is not None:
            results.append(signal)

    results.sort(key=lambda s: abs(s["conviction"]), reverse=True)
    return {"signals": results, "count": len(results)}


@router.get("/{symbol}")
async def get_signal(symbol: str):
    """Analyze a single symbol."""
    provider = get_data_provider()
    analyzer = SignalAnalyzer(provider)
    return await analyzer.analyze(symbol.upper())
