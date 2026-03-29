"""
yfinance data provider — used for TSX .TO symbols.

yfinance is free and supports Canadian stocks via the .TO suffix.
Rate limits are informal (~2,000 req/hour); we add a 60-second cache.

Docs: https://pypi.org/project/yfinance/
"""

import logging
from datetime import datetime, timezone

import yfinance as yf

from app.engine.data_provider import DataProvider

logger = logging.getLogger(__name__)


class YFinanceDataProvider(DataProvider):
    def __init__(self):
        self._cache: dict[str, tuple[float, object]] = {}

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

        try:
            ticker = yf.Ticker(symbol)
            # 1d period with 5m interval gives up to 78 bars for today
            df = ticker.history(period="1d", interval="5m")
            if df.empty:
                # Try 5d in case today has no data yet (pre-market)
                df = ticker.history(period="5d", interval="5m")
        except Exception as e:
            logger.error(f"yfinance intraday error for {symbol}: {e}")
            return []

        if df.empty:
            logger.warning(f"yfinance: no intraday data for {symbol}")
            return []

        bars_data = []
        for ts, row in df.iterrows():
            # ts is a pandas Timestamp; convert to UTC-aware datetime
            if hasattr(ts, "to_pydatetime"):
                dt = ts.to_pydatetime()
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = datetime.now(timezone.utc)

            bars_data.append({
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]),
                "timestamp": dt.isoformat(),
            })

        bars_data = bars_data[-bars:]
        self._store(cache_key, bars_data)
        return bars_data

    async def get_daily(self, symbol: str, days: int = 60) -> list[dict]:
        cache_key = f"daily_{symbol}_{days}"
        cached = self._cached(cache_key, ttl=300)
        if cached is not None:
            return cached  # type: ignore[return-value]

        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=f"{days + 10}d", interval="1d")
        except Exception as e:
            logger.error(f"yfinance daily error for {symbol}: {e}")
            return []

        if df.empty:
            logger.warning(f"yfinance: no daily data for {symbol}")
            return []

        bars_data = []
        for ts, row in df.iterrows():
            if hasattr(ts, "to_pydatetime"):
                dt = ts.to_pydatetime()
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = datetime.now(timezone.utc)

            bars_data.append({
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]),
                "timestamp": dt.isoformat(),
            })

        bars_data = bars_data[-days:]
        self._store(cache_key, bars_data)
        return bars_data

    async def get_quote(self, symbol: str) -> dict:
        bars = await self.get_intraday(symbol)
        if not bars:
            return {
                "symbol": symbol, "price": 0.0, "change": 0.0,
                "change_pct": 0.0, "volume": 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
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
