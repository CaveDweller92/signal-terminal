"""
Massive.com data provider.

Uses the v2 Aggregates API for OHLCV data.
Docs: https://massive.com/docs/rest/quickstart

Docs: https://massive.com/docs/rest/quickstart
"""

import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.engine.data_provider import DataProvider

logger = logging.getLogger(__name__)

_BASE = "https://api.massive.com"


class MassiveDataProvider(DataProvider):
    def __init__(self, api_key: str):
        self._key = api_key
        self._cache: dict[str, tuple[float, object]] = {}  # key → (fetched_at, data)
        self._client = httpx.AsyncClient(timeout=10.0)

    def _cached(self, key: str, ttl: int) -> object | None:
        if key in self._cache:
            fetched_at, data = self._cache[key]
            if datetime.now(timezone.utc).timestamp() - fetched_at < ttl:
                return data
        return None

    def _store(self, key: str, data: object) -> None:
        self._cache[key] = (datetime.now(timezone.utc).timestamp(), data)

    async def get_intraday(self, symbol: str, bars: int = 78) -> list[dict]:
        cache_key = f"intraday_{symbol}_{bars}"
        cached = self._cached(cache_key, ttl=60)
        if cached is not None:
            return cached  # type: ignore[return-value]

        # Try today first; fall back to previous trading day if empty
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        for days_back in range(0, 5):
            date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
            url = (
                f"{_BASE}/v2/aggs/ticker/{symbol}/range/5/minute/{date}/{date}"
                f"?adjusted=true&sort=asc&limit={bars}&apiKey={self._key}"
            )
            try:
                resp = await self._client.get(url)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.error(f"Massive intraday error for {symbol}: {e}")
                return []

            results = data.get("results") or []
            if results:
                if date != today:
                    logger.info(
                        "Massive: no data for %s on %s — using %s (%d days back)",
                        symbol, today, date, days_back,
                    )
                bars_data = [_massive_bar(r) for r in results[-bars:]]
                self._store(cache_key, bars_data)
                return bars_data

        logger.warning(f"Massive: no intraday data found for {symbol}")
        return []

    async def get_daily(self, symbol: str, days: int = 60) -> list[dict]:
        cache_key = f"daily_{symbol}_{days}"
        cached = self._cached(cache_key, ttl=300)
        if cached is not None:
            return cached  # type: ignore[return-value]

        to_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        from_date = (datetime.now(timezone.utc) - timedelta(days=days + 10)).strftime("%Y-%m-%d")
        url = (
            f"{_BASE}/v2/aggs/ticker/{symbol}/range/1/day/{from_date}/{to_date}"
            f"?adjusted=true&sort=asc&limit={days}&apiKey={self._key}"
        )
        try:
            resp = await self._client.get(url)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"Massive daily error for {symbol}: {e}")
            return []

        results = data.get("results") or []
        bars_data = [_massive_bar(r) for r in results[-days:]]
        self._store(cache_key, bars_data)
        return bars_data

    async def get_quote(self, symbol: str) -> dict:
        bars = await self.get_intraday(symbol)
        if not bars:
            return {"symbol": symbol, "price": 0.0, "change": 0.0, "change_pct": 0.0,
                    "volume": 0, "timestamp": datetime.now(timezone.utc).isoformat()}
        latest = bars[-1]
        prev = bars[-2]["close"] if len(bars) > 1 else latest["open"]
        change = latest["close"] - prev
        change_pct = (change / prev * 100) if prev else 0.0
        return {
            "symbol": symbol,
            "price": latest["close"],
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "volume": latest["volume"],
            "timestamp": latest["timestamp"],
        }


def _massive_bar(r: dict) -> dict:
    """Convert a Massive aggregate result to our standard bar format."""
    ts = datetime.fromtimestamp(r["t"] / 1000, tz=timezone.utc)
    return {
        "open": round(float(r["o"]), 2),
        "high": round(float(r["h"]), 2),
        "low": round(float(r["l"]), 2),
        "close": round(float(r["c"]), 2),
        "volume": int(r.get("v", 0)),
        "timestamp": ts.isoformat(),
    }
