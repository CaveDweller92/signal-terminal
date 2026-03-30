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
        self._client = httpx.AsyncClient(timeout=10.0)

    async def get_intraday(self, symbol: str, bars: int = 78) -> list[dict]:
        # Try today first; fall back to previous trading day if empty
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        for days_back in range(0, 5):
            date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
            # Request more than we need — market day can have 120+ bars,
            # but we only keep the last N. This avoids pagination for most cases.
            fetch_limit = max(bars, 500)
            url: str | None = (
                f"{_BASE}/v2/aggs/ticker/{symbol}/range/5/minute/{date}/{date}"
                f"?adjusted=true&sort=asc&limit={fetch_limit}&apiKey={self._key}"
            )

            all_results: list[dict] = []
            try:
                # Follow pagination to collect all available bars
                while url and len(all_results) < bars:
                    resp = await self._client.get(url)
                    resp.raise_for_status()
                    data = resp.json()
                    page_results = data.get("results") or []
                    all_results.extend(page_results)
                    next_url = data.get("next_url")
                    url = f"{next_url}&apiKey={self._key}" if next_url else None
            except Exception as e:
                logger.error(f"Massive intraday error for {symbol}: {e}")
                return []

            if all_results:
                if date != today:
                    logger.info(
                        "Massive: no data for %s on %s — using %s (%d days back)",
                        symbol, today, date, days_back,
                    )
                return [_massive_bar(r) for r in all_results[-bars:]]

        logger.warning(f"Massive: no intraday data found for {symbol}")
        return []

    async def get_daily(self, symbol: str, days: int = 60) -> list[dict]:
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
        return [_massive_bar(r) for r in results[-days:]]

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
