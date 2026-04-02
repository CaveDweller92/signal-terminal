"""
Signal API routes.

GET /api/signals           — return cached signals (re-analyzed every 5 min)
GET /api/signals/{symbol}  — analyze a single symbol (cached per-symbol)
"""

import json
import logging
from datetime import date, datetime, timezone

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.config import settings
from app.db.database import async_session
from app.engine.data_provider import get_data_provider
from app.engine.signal_service import SignalService
from app.models.screener_result import ScreenerResult
from app.models.watchlist import DailyWatchlist

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/signals", tags=["signals"])

_CACHE_TTL = 15 * 60  # 15 minutes — swing trading

_redis = None


async def _get_redis():
    global _redis
    if _redis is None:
        import redis.asyncio as aioredis
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


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
    refresh: bool = Query(False, description="Force re-analysis, ignoring cache."),
):
    """
    Analyze multiple symbols and return their signals.

    Results are cached in Redis for 5 minutes to avoid repeated
    API calls (Finnhub + Claude sentiment) on every page load.
    """
    if symbols:
        symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    else:
        symbol_list = await _resolve_symbols()

    if not symbol_list:
        return {"signals": [], "count": 0, "message": "No watchlist yet — run the screener first."}

    # Try Redis cache first
    cache_key = "signals:" + ",".join(sorted(symbol_list))
    if not refresh:
        try:
            r = await _get_redis()
            cached = await r.get(cache_key)
            if cached:
                data = json.loads(cached)
                data["cached"] = True
                return data
        except Exception as e:
            logger.debug("Redis cache read failed: %s", e)

    # Cache miss — run analysis and persist to DB
    provider = get_data_provider()
    async with async_session() as session:
        service = SignalService(session, provider)
        results = await service.analyze_batch(symbol_list)
        await session.commit()

    results.sort(key=lambda s: abs(s["conviction"]), reverse=True)
    now = datetime.now(timezone.utc).isoformat()
    data = {"signals": results, "count": len(results), "fetched_at": now}

    # Store in Redis
    try:
        r = await _get_redis()
        await r.set(cache_key, json.dumps(data), ex=_CACHE_TTL)
    except Exception as e:
        logger.debug("Redis cache write failed: %s", e)

    data["cached"] = False
    logger.info("Signals refreshed: %d symbols at %s", len(results), now)
    return data


@router.get("/{symbol}")
async def get_signal(symbol: str):
    """Analyze a single symbol (cached per-symbol for 5 min)."""
    symbol = symbol.upper()
    cache_key = f"signal:{symbol}"

    try:
        r = await _get_redis()
        cached = await r.get(cache_key)
        if cached:
            data = json.loads(cached)
            data["cached"] = True
            return data
    except Exception as e:
        logger.debug("Redis cache read failed: %s", e)

    provider = get_data_provider()
    async with async_session() as session:
        service = SignalService(session, provider)
        data = await service.analyze_and_persist(symbol)
        await session.commit()

    if data is not None:
        try:
            r = await _get_redis()
            await r.set(cache_key, json.dumps(data), ex=_CACHE_TTL)
        except Exception as e:
            logger.debug("Redis cache write failed: %s", e)

    return data
