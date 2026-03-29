from abc import ABC, abstractmethod

from app.config import settings


class DataProvider(ABC):
    """
    Interface for market data. The rest of the app calls these methods
    and doesn't care whether the data is from Massive or yfinance.
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


def get_data_provider() -> DataProvider:
    """
    Returns HybridDataProvider:
      - US symbols  → Massive.com  (requires MASSIVE_API_KEY)
      - .TO symbols → yfinance

    Raises RuntimeError if MASSIVE_API_KEY is not configured.
    """
    if not settings.massive_api_key:
        raise RuntimeError(
            "MASSIVE_API_KEY is not set. Add it to your .env file to fetch real market data."
        )
    from app.engine.hybrid_provider import HybridDataProvider
    return HybridDataProvider(settings.massive_api_key)
