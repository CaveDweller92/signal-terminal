"""
Discovery API routes.

POST /api/discovery/scan       — trigger pre-market screener
POST /api/discovery/watchlist   — trigger AI watchlist build
GET  /api/discovery/screener    — get today's screener results
GET  /api/discovery/watchlist   — get today's watchlist
GET  /api/discovery/universe    — get all tracked stocks
POST /api/discovery/seed        — seed the stock universe
"""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.engine.data_provider import get_data_provider
from app.engine.regime import RegimeDetector
from app.discovery.universe import seed_universe, get_active_symbols
from app.discovery.screener import PremarketScreener
from app.discovery.ai_watchlist import build_watchlist
from app.models.screener_result import ScreenerResult
from app.models.watchlist import DailyWatchlist
from app.schemas.discovery import (
    ScanResponse,
    ScreenerResultResponse,
    WatchlistEntryResponse,
    WatchlistResponse,
    StockUniverseResponse,
)

router = APIRouter(prefix="/api/discovery", tags=["discovery"])


@router.post("/seed")
async def seed_universe_endpoint(db: AsyncSession = Depends(get_db)):
    """Seed the stock universe with S&P 500, NASDAQ 100, and TSX stocks."""
    counts = await seed_universe(db)
    total = sum(counts.values())
    return {"message": f"Seeded {total} stocks", "counts": counts}


@router.get("/universe")
async def get_universe(
    universe: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get all tracked stocks, optionally filtered by universe."""
    stocks = await get_active_symbols(db, universe)
    return {
        "stocks": [StockUniverseResponse.model_validate(s) for s in stocks],
        "count": len(stocks),
    }


@router.post("/scan")
async def run_scan(db: AsyncSession = Depends(get_db)):
    """
    Trigger the pre-market screener.
    Scans all active stocks and saves top 30 to screener_results.
    """
    stocks = await get_active_symbols(db)
    if not stocks:
        return {"error": "No stocks in universe. Run POST /api/discovery/seed first."}

    provider = get_data_provider()
    screener = PremarketScreener(provider)
    results = await screener.scan(stocks, db)

    return ScanResponse(
        scan_date=date.today(),
        stocks_scanned=len(stocks),
        results_saved=len(results),
        top_results=[ScreenerResultResponse.model_validate(r) for r in results],
    )


@router.get("/screener")
async def get_screener_results(db: AsyncSession = Depends(get_db)):
    """Get today's screener results."""
    query = (
        select(ScreenerResult)
        .where(ScreenerResult.scan_date == date.today())
        .order_by(ScreenerResult.composite_score.desc())
    )
    result = await db.execute(query)
    results = list(result.scalars().all())

    return {
        "scan_date": date.today(),
        "results": [ScreenerResultResponse.model_validate(r) for r in results],
        "count": len(results),
    }


@router.post("/watchlist")
async def build_watchlist_endpoint(db: AsyncSession = Depends(get_db)):
    """
    Trigger the AI watchlist builder.
    Uses Claude to pick 12 stocks from today's screener results.
    Falls back to top 12 by score if Claude API is unavailable.
    """
    # Get current regime for context
    provider = get_data_provider()
    detector = RegimeDetector(provider)
    regime_result = await detector.detect()
    regime = regime_result["regime"]

    watchlist = await build_watchlist(db, regime=regime)

    if not watchlist:
        return {"error": "No screener results for today. Run POST /api/discovery/scan first."}

    return WatchlistResponse(
        watch_date=date.today(),
        picks=[WatchlistEntryResponse.model_validate(w) for w in watchlist],
        source="ai" if __import__("app.config", fromlist=["settings"]).settings.has_anthropic_key else "screener",
    )


@router.get("/watchlist")
async def get_watchlist(db: AsyncSession = Depends(get_db)):
    """Get today's watchlist."""
    query = (
        select(DailyWatchlist)
        .where(DailyWatchlist.watch_date == date.today())
        .order_by(DailyWatchlist.screener_rank)
    )
    result = await db.execute(query)
    entries = list(result.scalars().all())

    return {
        "watch_date": date.today(),
        "picks": [WatchlistEntryResponse.model_validate(e) for e in entries],
        "count": len(entries),
    }
