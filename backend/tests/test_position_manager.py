"""
Tests for positions/manager.py — position lifecycle and P&L calculations.

The manager handles money calculations. Wrong P&L = user makes decisions
on incorrect data. This is the most dangerous code to get wrong.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.positions.manager import PositionManager


def make_mock_db():
    """Create a mock async DB session."""
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.get = AsyncMock()
    db.execute = AsyncMock()
    return db


def make_mock_provider():
    """Create a mock data provider with realistic bars."""
    provider = AsyncMock()

    # Simulate intraday bars for AAPL ~190
    bars = []
    for i in range(78):
        price = 190.0 + (i - 39) * 0.1
        bars.append({
            "open": price - 0.05,
            "high": price + 0.5,
            "low": price - 0.5,
            "close": price,
            "volume": 1000000,
            "timestamp": f"2026-03-26T{9 + i // 12}:{(i % 12) * 5:02d}:00",
        })
    provider.get_intraday = AsyncMock(return_value=bars)

    # Daily bars
    daily = []
    for i in range(60):
        price = 185.0 + i * 0.1
        daily.append({
            "open": price - 0.3,
            "high": price + 1.5,
            "low": price - 1.5,
            "close": price,
            "volume": 5000000,
            "timestamp": f"2026-{1 + i // 30:02d}-{1 + i % 28:02d}",
        })
    provider.get_daily = AsyncMock(return_value=daily)

    return provider


class TestOpenPosition:
    @pytest.mark.asyncio
    async def test_creates_position_with_defaults(self):
        db = make_mock_db()
        provider = make_mock_provider()
        manager = PositionManager(db, provider)

        with patch("app.positions.manager.RegimeDetector") as MockDetector:
            MockDetector.return_value.detect = AsyncMock(
                return_value={"regime": "trending_up", "confidence": 0.8}
            )

            position = await manager.open_position({
                "symbol": "AAPL",
                "direction": "LONG",
                "entry_price": 190.0,
                "quantity": 100,
            })

        # Should have been added to DB
        db.add.assert_called_once()
        db.flush.assert_called_once()

        # Check the position object
        assert position.symbol == "AAPL"
        assert position.direction == "LONG"
        assert position.status == "OPEN"
        assert position.entry_price == 190.0
        assert position.quantity == 100
        assert position.stop_loss_price is not None
        assert position.profit_target_price is not None
        assert position.atr_value_at_entry > 0
        assert position.regime_at_entry == "trending_up"

    @pytest.mark.asyncio
    async def test_stop_loss_below_entry_for_long(self):
        db = make_mock_db()
        provider = make_mock_provider()
        manager = PositionManager(db, provider)

        with patch("app.positions.manager.RegimeDetector") as MockDetector:
            MockDetector.return_value.detect = AsyncMock(
                return_value={"regime": "low_volatility", "confidence": 0.7}
            )

            position = await manager.open_position({
                "symbol": "AAPL",
                "direction": "LONG",
                "entry_price": 190.0,
                "quantity": 50,
            })

        assert position.stop_loss_price < position.entry_price
        assert position.profit_target_price > position.entry_price

    @pytest.mark.asyncio
    async def test_stop_loss_above_entry_for_short(self):
        db = make_mock_db()
        provider = make_mock_provider()
        manager = PositionManager(db, provider)

        with patch("app.positions.manager.RegimeDetector") as MockDetector:
            MockDetector.return_value.detect = AsyncMock(
                return_value={"regime": "trending_down", "confidence": 0.75}
            )

            position = await manager.open_position({
                "symbol": "AAPL",
                "direction": "SHORT",
                "entry_price": 190.0,
                "quantity": 50,
            })

        assert position.stop_loss_price > position.entry_price
        assert position.profit_target_price < position.entry_price

    @pytest.mark.asyncio
    async def test_user_can_override_exits(self):
        db = make_mock_db()
        provider = make_mock_provider()
        manager = PositionManager(db, provider)

        with patch("app.positions.manager.RegimeDetector") as MockDetector:
            MockDetector.return_value.detect = AsyncMock(
                return_value={"regime": "mean_reverting", "confidence": 0.6}
            )

            position = await manager.open_position({
                "symbol": "AAPL",
                "direction": "LONG",
                "entry_price": 190.0,
                "quantity": 100,
                "stop_loss_price": 180.0,
                "profit_target_price": 210.0,
            })

        assert position.stop_loss_price == 180.0
        assert position.profit_target_price == 210.0


class TestClosePosition:
    @pytest.mark.asyncio
    async def test_pnl_calculation_long_profit(self):
        db = make_mock_db()
        provider = make_mock_provider()
        manager = PositionManager(db, provider)

        # Create a mock position in DB
        mock_position = MagicMock()
        mock_position.status = "OPEN"
        mock_position.direction = "LONG"
        mock_position.entry_price = 190.0
        mock_position.quantity = 100
        mock_position.entry_signal_id = None
        db.get = AsyncMock(return_value=mock_position)

        with patch("app.positions.manager.RegimeDetector") as MockDetector:
            MockDetector.return_value.detect = AsyncMock(
                return_value={"regime": "trending_up", "confidence": 0.8}
            )

            position = await manager.close_position(1, exit_price=200.0)

        # Long: bought at 190, sold at 200 → +5.26%
        expected_pnl_pct = (200.0 - 190.0) / 190.0 * 100
        assert position.realized_pnl_pct == pytest.approx(expected_pnl_pct, abs=0.01)
        assert position.realized_pnl_pct > 0
        assert position.status == "CLOSED"
        assert position.exit_reason == "manual"

    @pytest.mark.asyncio
    async def test_pnl_calculation_long_loss(self):
        db = make_mock_db()
        provider = make_mock_provider()
        manager = PositionManager(db, provider)

        mock_position = MagicMock()
        mock_position.status = "OPEN"
        mock_position.direction = "LONG"
        mock_position.entry_price = 190.0
        mock_position.quantity = 100
        mock_position.entry_signal_id = None
        db.get = AsyncMock(return_value=mock_position)

        with patch("app.positions.manager.RegimeDetector") as MockDetector:
            MockDetector.return_value.detect = AsyncMock(
                return_value={"regime": "volatile_choppy", "confidence": 0.7}
            )

            position = await manager.close_position(1, exit_price=185.0)

        expected_pnl_pct = (185.0 - 190.0) / 190.0 * 100
        assert position.realized_pnl_pct == pytest.approx(expected_pnl_pct, abs=0.01)
        assert position.realized_pnl_pct < 0

    @pytest.mark.asyncio
    async def test_pnl_calculation_short_profit(self):
        db = make_mock_db()
        provider = make_mock_provider()
        manager = PositionManager(db, provider)

        mock_position = MagicMock()
        mock_position.status = "OPEN"
        mock_position.direction = "SHORT"
        mock_position.entry_price = 190.0
        mock_position.quantity = 100
        mock_position.entry_signal_id = None
        db.get = AsyncMock(return_value=mock_position)

        with patch("app.positions.manager.RegimeDetector") as MockDetector:
            MockDetector.return_value.detect = AsyncMock(
                return_value={"regime": "trending_down", "confidence": 0.8}
            )

            position = await manager.close_position(1, exit_price=180.0)

        # Short: sold at 190, bought back at 180 → +5.26%
        expected_pnl_pct = (190.0 - 180.0) / 190.0 * 100
        assert position.realized_pnl_pct == pytest.approx(expected_pnl_pct, abs=0.01)
        assert position.realized_pnl_pct > 0

    @pytest.mark.asyncio
    async def test_pnl_dollar_calculation(self):
        db = make_mock_db()
        provider = make_mock_provider()
        manager = PositionManager(db, provider)

        mock_position = MagicMock()
        mock_position.status = "OPEN"
        mock_position.direction = "LONG"
        mock_position.entry_price = 100.0
        mock_position.quantity = 50
        mock_position.entry_signal_id = None
        db.get = AsyncMock(return_value=mock_position)

        with patch("app.positions.manager.RegimeDetector") as MockDetector:
            MockDetector.return_value.detect = AsyncMock(
                return_value={"regime": "trending_up", "confidence": 0.8}
            )

            position = await manager.close_position(1, exit_price=110.0)

        # 10% gain on $100 × 50 shares = $500
        assert position.realized_pnl_dollar == pytest.approx(500.0, abs=1.0)

    @pytest.mark.asyncio
    async def test_close_nonexistent_position_raises(self):
        db = make_mock_db()
        provider = make_mock_provider()
        manager = PositionManager(db, provider)
        db.get = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="not found"):
            await manager.close_position(999, exit_price=200.0)

    @pytest.mark.asyncio
    async def test_close_already_closed_raises(self):
        db = make_mock_db()
        provider = make_mock_provider()
        manager = PositionManager(db, provider)

        mock_position = MagicMock()
        mock_position.status = "CLOSED"
        db.get = AsyncMock(return_value=mock_position)

        with pytest.raises(ValueError, match="not found or already closed"):
            await manager.close_position(1, exit_price=200.0)


class TestATRCalculation:
    def test_atr_with_sufficient_bars(self):
        db = make_mock_db()
        provider = make_mock_provider()
        manager = PositionManager(db, provider)

        bars = []
        for i in range(20):
            bars.append({
                "open": 100.0, "high": 102.0, "low": 98.0,
                "close": 100.0 + i * 0.1, "volume": 1000000,
            })

        atr = manager._calc_atr(bars)
        assert atr > 0

    def test_atr_with_insufficient_bars(self):
        db = make_mock_db()
        provider = make_mock_provider()
        manager = PositionManager(db, provider)

        bars = [{"open": 100.0, "high": 103.0, "low": 97.0, "close": 101.0, "volume": 1000000}]
        atr = manager._calc_atr(bars)
        # Fallback: high - low of last bar
        assert atr == pytest.approx(6.0)
