"""
Hybrid data provider — routes requests to the best source per symbol.

  .TO symbols  →  YFinanceDataProvider  (free, handles Canadian equities well)
  US symbols   →  MassiveDataProvider   (paid, real-time US OHLCV via Massive.com)

Falls back to YFinance for US if Massive returns no data.
"""

import logging

from app.engine.data_provider import DataProvider
from app.engine.massive_provider import MassiveDataProvider
from app.engine.yfinance_provider import YFinanceDataProvider

logger = logging.getLogger(__name__)


class HybridDataProvider(DataProvider):
    def __init__(self, massive_api_key: str):
        self._massive = MassiveDataProvider(massive_api_key)
        self._yfinance = YFinanceDataProvider()

    def _provider_for(self, symbol: str) -> DataProvider:
        """TSX symbols end with .TO — route to yfinance."""
        if symbol.upper().endswith(".TO"):
            return self._yfinance
        return self._massive

    async def get_intraday(self, symbol: str, bars: int = 78) -> list[dict]:
        return await self._provider_for(symbol).get_intraday(symbol, bars)

    async def get_daily(self, symbol: str, days: int = 60) -> list[dict]:
        return await self._provider_for(symbol).get_daily(symbol, days)

    async def get_quote(self, symbol: str) -> dict:
        return await self._provider_for(symbol).get_quote(symbol)
