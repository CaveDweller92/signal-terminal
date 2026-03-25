import random
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

import numpy as np

from app.config import settings


class DataProvider(ABC):
    """
    Interface for market data. The rest of the app calls these methods
    and doesn't care whether the data is simulated or from Polygon/Finnhub.
    """

    @abstractmethod
    async def get_intraday(self, symbol: str, bars: int = 78) -> list[dict]:
        """
        Returns N most recent intraday bars (5-min intervals).
        78 bars = one full trading day (9:30 AM - 4:00 PM = 6.5 hours × 12 bars/hour).

        Each bar: {open, high, low, close, volume, timestamp}
        """
        ...

    @abstractmethod
    async def get_daily(self, symbol: str, days: int = 60) -> list[dict]:
        """
        Returns N most recent daily bars.
        Used for ATR calculation, regime detection, and longer-term analysis.
        """
        ...

    @abstractmethod
    async def get_quote(self, symbol: str) -> dict:
        """
        Returns latest price snapshot.
        {symbol, price, change, change_pct, volume, timestamp}
        """
        ...


class SimulatedDataProvider(DataProvider):
    """
    Generates fake but realistic OHLCV data using random walks.

    Each symbol gets a deterministic seed so the same symbol always
    produces consistent price behavior within a session (AAPL won't
    randomly jump from $190 to $50 between calls).

    Price model:
    - Base price seeded from symbol hash (so AAPL ≈ $190, TSLA ≈ $250, etc.)
    - Geometric Brownian Motion with mean reversion (prevents runaway prices)
    - Intraday: smaller moves with volume U-shape (high at open/close, low midday)
    - Random catalysts: occasional gaps and volume spikes
    """

    # Realistic base prices for common symbols
    SYMBOL_BASES: dict[str, float] = {
        "AAPL": 190.0, "MSFT": 420.0, "GOOGL": 175.0, "AMZN": 185.0,
        "NVDA": 920.0, "META": 500.0, "TSLA": 250.0, "AMD": 160.0,
        "NFLX": 620.0, "JPM": 195.0, "V": 280.0, "UNH": 520.0,
        "HD": 370.0, "DIS": 110.0, "PYPL": 65.0, "INTC": 32.0,
        "BA": 180.0, "CRM": 270.0, "COST": 730.0, "PEP": 170.0,
        "SHOP": 95.0, "TD": 78.0, "RY": 130.0, "ENB": 48.0,
        "BMO": 120.0, "BNS": 65.0, "CP": 110.0, "CNR": 160.0,
    }

    def __init__(self):
        self._cache: dict[str, dict] = {}

    def _get_base_price(self, symbol: str) -> float:
        if symbol in self.SYMBOL_BASES:
            return self.SYMBOL_BASES[symbol]
        # Deterministic price from symbol hash (range $20-$500)
        h = hash(symbol) % 10000
        return 20.0 + (h / 10000) * 480.0

    def _get_rng(self, symbol: str, seed_offset: int = 0) -> np.random.Generator:
        """Deterministic RNG per symbol + date so data is consistent within a day."""
        today = datetime.utcnow().strftime("%Y%m%d")
        seed = hash(f"{symbol}_{today}_{seed_offset}") % (2**31)
        return np.random.default_rng(seed)

    async def get_intraday(self, symbol: str, bars: int = 78) -> list[dict]:
        cache_key = f"intraday_{symbol}_{bars}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        rng = self._get_rng(symbol, seed_offset=1)
        base = self._get_base_price(symbol)

        # Volatility scaled to price (higher priced stocks move more in absolute terms)
        daily_vol = base * 0.02  # ~2% daily range
        bar_vol = daily_vol / np.sqrt(bars)

        # Generate price path using geometric random walk
        returns = rng.normal(0, bar_vol / base, size=bars)

        # Add slight trend bias (random per day)
        trend = rng.normal(0, 0.001)
        returns += trend

        # Mean reversion toward base (prevents drift over many bars)
        prices = np.empty(bars)
        prices[0] = base * (1 + rng.normal(0, 0.005))  # Small opening gap

        for i in range(1, bars):
            reversion = -0.01 * (prices[i - 1] - base) / base
            prices[i] = prices[i - 1] * (1 + returns[i] + reversion)

        # Generate OHLCV from close prices
        result = []
        now = datetime.utcnow().replace(hour=9, minute=30, second=0, microsecond=0)

        for i in range(bars):
            close = prices[i]

            # Intrabar range: random high/low around close
            bar_range = abs(rng.normal(0, bar_vol * 0.6))
            high = close + abs(rng.normal(0, bar_range))
            low = close - abs(rng.normal(0, bar_range))
            low = max(low, close * 0.99)  # Floor to prevent negative

            # Open: close of previous bar with small gap
            if i == 0:
                open_price = base
            else:
                open_price = prices[i - 1] * (1 + rng.normal(0, 0.0005))

            # Ensure OHLC consistency
            high = max(high, open_price, close)
            low = min(low, open_price, close)

            # Volume: U-shaped intraday pattern (high at open/close, low midday)
            hour_frac = i / bars
            u_shape = 2.0 * (hour_frac - 0.5) ** 2 + 0.5
            base_volume = rng.integers(50_000, 500_000)
            volume = int(base_volume * u_shape)

            # Random volume spikes (5% chance per bar)
            if rng.random() < 0.05:
                volume = int(volume * rng.uniform(2.0, 5.0))

            timestamp = now + timedelta(minutes=5 * i)

            result.append({
                "open": round(float(open_price), 2),
                "high": round(float(high), 2),
                "low": round(float(low), 2),
                "close": round(float(close), 2),
                "volume": volume,
                "timestamp": timestamp.isoformat(),
            })

        self._cache[cache_key] = result
        return result

    async def get_daily(self, symbol: str, days: int = 60) -> list[dict]:
        cache_key = f"daily_{symbol}_{days}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        rng = self._get_rng(symbol, seed_offset=2)
        base = self._get_base_price(symbol)

        # Daily returns: slightly higher volatility than intrabar
        daily_vol = 0.015  # ~1.5% daily std dev
        returns = rng.normal(0.0003, daily_vol, size=days)  # Slight upward drift

        prices = np.empty(days)
        prices[0] = base * (1 + rng.normal(0, 0.02))

        for i in range(1, days):
            reversion = -0.005 * (prices[i - 1] - base) / base
            prices[i] = prices[i - 1] * (1 + returns[i] + reversion)

        result = []
        today = datetime.utcnow().date()

        for i in range(days):
            close = prices[i]
            day_range = close * rng.uniform(0.01, 0.03)

            high = close + abs(rng.normal(0, day_range * 0.5))
            low = close - abs(rng.normal(0, day_range * 0.5))
            low = max(low, close * 0.95)

            if i == 0:
                open_price = base
            else:
                open_price = prices[i - 1] * (1 + rng.normal(0, 0.003))

            high = max(high, open_price, close)
            low = min(low, open_price, close)

            volume = int(rng.integers(1_000_000, 20_000_000))

            bar_date = today - timedelta(days=days - i)

            result.append({
                "open": round(float(open_price), 2),
                "high": round(float(high), 2),
                "low": round(float(low), 2),
                "close": round(float(close), 2),
                "volume": volume,
                "timestamp": bar_date.isoformat(),
            })

        self._cache[cache_key] = result
        return result

    async def get_quote(self, symbol: str) -> dict:
        bars = await self.get_intraday(symbol, bars=78)
        latest = bars[-1]
        prev_close = bars[-2]["close"] if len(bars) > 1 else latest["open"]

        change = latest["close"] - prev_close
        change_pct = (change / prev_close) * 100 if prev_close else 0

        return {
            "symbol": symbol,
            "price": latest["close"],
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "volume": latest["volume"],
            "timestamp": latest["timestamp"],
        }


def get_data_provider() -> DataProvider:
    """
    Factory — returns simulated or real provider based on config.
    Real providers will be added in Phase 3.
    """
    if settings.use_simulated_data:
        return SimulatedDataProvider()

    # TODO: Phase 3 — return PolygonDataProvider() or FinnhubDataProvider()
    return SimulatedDataProvider()
