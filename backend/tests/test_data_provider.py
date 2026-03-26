"""
Tests for engine/data_provider.py — simulated market data.

The data provider feeds everything downstream. If it produces
negative prices or inconsistent OHLCV, the whole system breaks.
"""

import pytest

from app.engine.data_provider import SimulatedDataProvider


@pytest.fixture
def provider():
    return SimulatedDataProvider()


class TestSimulatedDataProvider:
    @pytest.mark.asyncio
    async def test_intraday_returns_correct_count(self, provider):
        bars = await provider.get_intraday("AAPL", bars=78)
        assert len(bars) == 78

    @pytest.mark.asyncio
    async def test_intraday_bar_has_required_fields(self, provider):
        bars = await provider.get_intraday("AAPL")
        required = ["open", "high", "low", "close", "volume", "timestamp"]
        for bar in bars:
            for field in required:
                assert field in bar, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_ohlc_consistency(self, provider):
        """High >= max(open, close) and Low <= min(open, close)."""
        bars = await provider.get_intraday("MSFT")
        for bar in bars:
            assert bar["high"] >= bar["open"], f"High {bar['high']} < Open {bar['open']}"
            assert bar["high"] >= bar["close"], f"High {bar['high']} < Close {bar['close']}"
            assert bar["low"] <= bar["open"], f"Low {bar['low']} > Open {bar['open']}"
            assert bar["low"] <= bar["close"], f"Low {bar['low']} > Close {bar['close']}"

    @pytest.mark.asyncio
    async def test_prices_are_positive(self, provider):
        bars = await provider.get_intraday("AAPL")
        for bar in bars:
            assert bar["open"] > 0
            assert bar["high"] > 0
            assert bar["low"] > 0
            assert bar["close"] > 0

    @pytest.mark.asyncio
    async def test_volumes_are_positive(self, provider):
        bars = await provider.get_intraday("AAPL")
        for bar in bars:
            assert bar["volume"] > 0

    @pytest.mark.asyncio
    async def test_deterministic_per_symbol(self, provider):
        """Same symbol should produce same data within a session."""
        bars1 = await provider.get_intraday("AAPL")
        bars2 = await provider.get_intraday("AAPL")
        assert bars1[0]["close"] == bars2[0]["close"]
        assert bars1[-1]["close"] == bars2[-1]["close"]

    @pytest.mark.asyncio
    async def test_different_symbols_different_data(self, provider):
        bars_aapl = await provider.get_intraday("AAPL")
        bars_tsla = await provider.get_intraday("TSLA")
        assert bars_aapl[0]["close"] != bars_tsla[0]["close"]

    @pytest.mark.asyncio
    async def test_daily_returns_correct_count(self, provider):
        daily = await provider.get_daily("AAPL", days=60)
        assert len(daily) == 60

    @pytest.mark.asyncio
    async def test_daily_ohlc_consistency(self, provider):
        daily = await provider.get_daily("NVDA")
        for bar in daily:
            assert bar["high"] >= bar["close"]
            assert bar["low"] <= bar["close"]

    @pytest.mark.asyncio
    async def test_quote_returns_required_fields(self, provider):
        quote = await provider.get_quote("AAPL")
        required = ["symbol", "price", "change", "change_pct", "volume", "timestamp"]
        for field in required:
            assert field in quote

    @pytest.mark.asyncio
    async def test_quote_price_matches_last_bar(self, provider):
        bars = await provider.get_intraday("META")
        quote = await provider.get_quote("META")
        assert quote["price"] == bars[-1]["close"]

    @pytest.mark.asyncio
    async def test_known_symbol_has_realistic_price(self, provider):
        """AAPL should be around $190, not $5 or $5000."""
        bars = await provider.get_intraday("AAPL")
        price = bars[-1]["close"]
        assert 100 < price < 300

    @pytest.mark.asyncio
    async def test_unknown_symbol_still_works(self, provider):
        """Unknown symbols should generate valid data from hash."""
        bars = await provider.get_intraday("XYZZZ")
        assert len(bars) > 0
        assert bars[0]["close"] > 0
