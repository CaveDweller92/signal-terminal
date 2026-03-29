"""
Finnhub.io data provider.

Free tier supports real-time US stock quotes and intraday candles (1-min resolution).
We use 5-min resolution by aggregating 1-min bars, or using the closest supported
resolution (Finnhub supports: 1, 5, 15, 30, 60, D, W, M).

Docs: https://finnhub.io/docs/api
"""

import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.engine.data_provider import DataProvider

logger = logging.getLogger(__name__)

_BASE = "https://finnhub.io/api/v1"


class FinnhubDataProvider(DataProvider):
    def __init__(self, api_key: str):
        self._key = api_key
        self._cache: dict[str, tuple[float, object]] = {}
        self._client = httpx.AsyncClient(timeout=10.0)
        # Symbols that returned 403 — skip on future calls (requires paid plan)
        self._blocked: set[str] = set()

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

        now = datetime.now(timezone.utc)
        # Fetch a bit more than needed to cover non-trading minutes
        from_ts = int((now - timedelta(hours=8)).timestamp())
        to_ts = int(now.timestamp())

        url = (
            f"{_BASE}/stock/candle"
            f"?symbol={symbol}&resolution=5&from={from_ts}&to={to_ts}&token={self._key}"
        )
        try:
            resp = await self._client.get(url)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"Finnhub intraday error for {symbol}: {e}")
            return []

        if data.get("s") != "ok" or not data.get("c"):
            logger.warning(f"Finnhub: no intraday data for {symbol} (status={data.get('s')})")
            return []

        bars_data = [
            _finnhub_bar(
                data["o"][i], data["h"][i], data["l"][i],
                data["c"][i], data["v"][i], data["t"][i]
            )
            for i in range(len(data["c"]))
        ]
        bars_data = bars_data[-bars:]
        self._store(cache_key, bars_data)
        return bars_data

    async def get_daily(self, symbol: str, days: int = 60) -> list[dict]:
        cache_key = f"daily_{symbol}_{days}"
        cached = self._cached(cache_key, ttl=300)
        if cached is not None:
            return cached  # type: ignore[return-value]

        now = datetime.now(timezone.utc)
        from_ts = int((now - timedelta(days=days + 10)).timestamp())
        to_ts = int(now.timestamp())

        url = (
            f"{_BASE}/stock/candle"
            f"?symbol={symbol}&resolution=D&from={from_ts}&to={to_ts}&token={self._key}"
        )
        try:
            resp = await self._client.get(url)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"Finnhub daily error for {symbol}: {e}")
            return []

        if data.get("s") != "ok" or not data.get("c"):
            logger.warning(f"Finnhub: no daily data for {symbol}")
            return []

        bars_data = [
            _finnhub_bar(
                data["o"][i], data["h"][i], data["l"][i],
                data["c"][i], data["v"][i], data["t"][i]
            )
            for i in range(len(data["c"]))
        ]
        bars_data = bars_data[-days:]
        self._store(cache_key, bars_data)
        return bars_data

    async def get_quote(self, symbol: str) -> dict:
        url = f"{_BASE}/quote?symbol={symbol}&token={self._key}"
        try:
            resp = await self._client.get(url)
            resp.raise_for_status()
            q = resp.json()
        except Exception as e:
            logger.error(f"Finnhub quote error for {symbol}: {e}")
            bars = await self.get_intraday(symbol)
            if bars:
                latest = bars[-1]
                return {"symbol": symbol, "price": latest["close"], "change": 0.0,
                        "change_pct": 0.0, "volume": latest["volume"],
                        "timestamp": latest["timestamp"]}
            return {"symbol": symbol, "price": 0.0, "change": 0.0, "change_pct": 0.0,
                    "volume": 0, "timestamp": datetime.now(timezone.utc).isoformat()}

        price = q.get("c", 0.0)
        prev_close = q.get("pc", price)
        change = price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0.0
        return {
            "symbol": symbol,
            "price": round(float(price), 2),
            "change": round(float(change), 2),
            "change_pct": round(float(change_pct), 2),
            "volume": 0,  # not in quote endpoint
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def _finnhub_bar(o: float, h: float, l: float, c: float, v: float, t: int) -> dict:
    ts = datetime.fromtimestamp(t, tz=timezone.utc)
    return {
        "open": round(float(o), 2),
        "high": round(float(h), 2),
        "low": round(float(l), 2),
        "close": round(float(c), 2),
        "volume": int(v),
        "timestamp": ts.isoformat(),
    }
