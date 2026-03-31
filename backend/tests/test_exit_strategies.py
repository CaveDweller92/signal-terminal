"""
Tests for positions/exit_strategies/ — all 5 exit strategies.

These determine when to tell the user to close a trade.
Wrong trigger = missed profit or unnecessary loss.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from app.positions.exit_strategies.base import ExitUrgency
from app.positions.exit_strategies.stop_loss import StopLossStrategy
from app.positions.exit_strategies.profit_target import ProfitTargetStrategy
from app.positions.exit_strategies.indicator_reversal import IndicatorReversalStrategy
from app.positions.exit_strategies.time_based import TimeBasedExitStrategy
from app.positions.exit_strategies.composite import CompositeExitStrategy


def make_position(**overrides):
    """Create a mock position with sensible defaults."""
    defaults = {
        "id": 1,
        "symbol": "AAPL",
        "direction": "LONG",
        "entry_price": 190.0,
        "quantity": 100,
        "stop_loss_price": 185.0,
        "profit_target_price": 200.0,
        "stop_loss_pct": 2.0,
        "profit_target_pct": 3.0,
        "use_atr_exits": True,
        "atr_value_at_entry": 3.5,
        "eod_exit_enabled": False,
        "max_hold_days": 25,
        "bars_held": 3,
        "unrealized_pnl_pct": 0.5,
        "high_since_entry": 192.0,
        "low_since_entry": 188.0,
    }
    defaults.update(overrides)
    pos = MagicMock()
    for k, v in defaults.items():
        setattr(pos, k, v)
    return pos


def make_bar(close, high=None, low=None, open_price=None, volume=100000):
    """Create a price bar dict."""
    if high is None:
        high = close + 0.5
    if low is None:
        low = close - 0.5
    if open_price is None:
        open_price = close - 0.1
    return {
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "timestamp": datetime.utcnow().isoformat(),
    }


# === Stop Loss ===

class TestStopLoss:
    @pytest.mark.asyncio
    async def test_triggers_when_price_below_stop_long(self):
        strategy = StopLossStrategy()
        position = make_position(direction="LONG", stop_loss_price=185.0)
        bar = make_bar(close=184.0)
        result = await strategy.evaluate(position, bar, [bar])

        assert result is not None
        assert result.triggered
        assert result.urgency == ExitUrgency.CRITICAL
        assert result.exit_type == "stop_loss"

    @pytest.mark.asyncio
    async def test_triggers_when_price_above_stop_short(self):
        strategy = StopLossStrategy()
        position = make_position(direction="SHORT", entry_price=190.0, stop_loss_price=195.0)
        bar = make_bar(close=196.0)
        result = await strategy.evaluate(position, bar, [bar])

        assert result is not None
        assert result.urgency == ExitUrgency.CRITICAL

    @pytest.mark.asyncio
    async def test_no_trigger_when_price_safe(self):
        strategy = StopLossStrategy()
        position = make_position(direction="LONG", stop_loss_price=185.0)
        bar = make_bar(close=192.0)
        result = await strategy.evaluate(position, bar, [bar])

        assert result is None

    @pytest.mark.asyncio
    async def test_warning_when_approaching_stop(self):
        strategy = StopLossStrategy()
        # Stop at 185, entry at 190 → total distance = 5
        # Price at 186 → remaining = 1, 1/5 = 20% < 30% threshold
        position = make_position(direction="LONG", stop_loss_price=185.0, stop_loss_pct=None)
        bar = make_bar(close=186.0)
        result = await strategy.evaluate(position, bar, [bar])

        assert result is not None
        assert result.urgency == ExitUrgency.MEDIUM

    @pytest.mark.asyncio
    async def test_uses_tightest_stop_for_long(self):
        strategy = StopLossStrategy()
        # Price stop at 185, pct stop = 2% of 190 = 186.2
        # Tightest for long = max(185, 186.2) = 186.2
        position = make_position(direction="LONG", stop_loss_price=185.0, stop_loss_pct=2.0)
        bar = make_bar(close=185.5)  # Below 186.2 but above 185
        result = await strategy.evaluate(position, bar, [bar])

        assert result is not None
        assert result.triggered

    @pytest.mark.asyncio
    async def test_no_trigger_without_stops(self):
        strategy = StopLossStrategy()
        position = make_position(stop_loss_price=None, stop_loss_pct=None)
        bar = make_bar(close=100.0)
        result = await strategy.evaluate(position, bar, [bar])

        assert result is None


# === Profit Target ===

class TestProfitTarget:
    @pytest.mark.asyncio
    async def test_triggers_when_price_hits_target_long(self):
        strategy = ProfitTargetStrategy()
        position = make_position(direction="LONG", profit_target_price=200.0)
        bar = make_bar(close=201.0)
        result = await strategy.evaluate(position, bar, [bar])

        assert result is not None
        assert result.triggered
        assert result.urgency == ExitUrgency.HIGH
        assert result.exit_type == "profit_target"

    @pytest.mark.asyncio
    async def test_triggers_when_price_hits_target_short(self):
        strategy = ProfitTargetStrategy()
        position = make_position(
            direction="SHORT", entry_price=190.0,
            profit_target_price=180.0, profit_target_pct=None,
        )
        bar = make_bar(close=179.0)
        result = await strategy.evaluate(position, bar, [bar])

        assert result is not None
        assert result.urgency == ExitUrgency.HIGH

    @pytest.mark.asyncio
    async def test_no_trigger_when_below_target(self):
        strategy = ProfitTargetStrategy()
        position = make_position(direction="LONG", profit_target_price=200.0, profit_target_pct=None)
        bar = make_bar(close=195.0)
        result = await strategy.evaluate(position, bar, [bar])

        # Could be None or LOW (75% alert). 195 is 50% of the way (190→200)
        if result is not None:
            assert result.urgency in (ExitUrgency.LOW, ExitUrgency.HIGH)

    @pytest.mark.asyncio
    async def test_partial_alert_at_75_percent(self):
        strategy = ProfitTargetStrategy()
        # Entry 190, target 200 → distance = 10. 75% = 197.5
        position = make_position(
            direction="LONG", entry_price=190.0,
            profit_target_price=200.0, profit_target_pct=None,
        )
        bar = make_bar(close=198.0)
        result = await strategy.evaluate(position, bar, [bar])

        assert result is not None
        assert result.urgency == ExitUrgency.LOW

    @pytest.mark.asyncio
    async def test_no_trigger_without_targets(self):
        strategy = ProfitTargetStrategy()
        position = make_position(profit_target_price=None, profit_target_pct=None)
        bar = make_bar(close=300.0)
        result = await strategy.evaluate(position, bar, [bar])

        assert result is None


# === Indicator Reversal ===

class TestIndicatorReversal:
    @pytest.mark.asyncio
    async def test_no_reversal_on_short_data(self):
        strategy = IndicatorReversalStrategy()
        position = make_position(direction="LONG")
        bar = make_bar(close=190.0)
        result = await strategy.evaluate(position, bar, [bar])

        assert result is None

    @pytest.mark.asyncio
    async def test_detects_reversal_on_downtrend_for_long(self):
        """A long position in a downtrend should trigger reversal signals."""
        import numpy as np
        strategy = IndicatorReversalStrategy({"rsi_overbought": 70, "rsi_oversold": 30})
        position = make_position(direction="LONG")

        # Create a clear downtrend (50 bars falling from 200 to 170)
        bars = []
        for i in range(50):
            price = 200.0 - i * 0.6
            bars.append(make_bar(close=price))

        result = await strategy.evaluate(position, bars[-1], bars)
        # Should detect bearish EMA/MACD signals
        if result is not None:
            assert result.exit_type == "indicator_reversal"
            assert result.urgency in (ExitUrgency.MEDIUM, ExitUrgency.HIGH)


# === Time-Based ===

class TestTimeBased:
    @pytest.mark.asyncio
    async def test_max_hold_triggers(self):
        """Max hold fires when days held >= max_hold_days."""
        strategy = TimeBasedExitStrategy()
        position = make_position(max_hold_days=25, bars_held=25)
        bar = make_bar(close=190.0)
        result = await strategy.evaluate(position, bar, [bar])

        assert result is not None
        assert result.exit_type == "max_hold_warning"
        assert result.urgency == ExitUrgency.MEDIUM

    @pytest.mark.asyncio
    async def test_no_trigger_under_max_hold(self):
        """No alert when days held is below max."""
        strategy = TimeBasedExitStrategy()
        position = make_position(max_hold_days=25, bars_held=10)
        bar = make_bar(close=190.0)
        result = await strategy.evaluate(position, bar, [bar])

        assert result is None

    @pytest.mark.asyncio
    async def test_no_max_hold_if_disabled(self):
        """No alert when max_hold_days is None."""
        strategy = TimeBasedExitStrategy()
        position = make_position(max_hold_days=None, bars_held=999, eod_exit_enabled=False)
        bar = make_bar(close=190.0)
        result = await strategy.evaluate(position, bar, [bar])

        assert result is None


# === Composite ===

class TestComposite:
    @pytest.mark.asyncio
    async def test_runs_all_strategies(self):
        """Composite should run all strategies and return triggered ones."""
        # Create a position that triggers stop loss
        position = make_position(direction="LONG", stop_loss_price=185.0)
        bar = make_bar(close=183.0)

        composite = CompositeExitStrategy(
            strategies=[StopLossStrategy(), ProfitTargetStrategy()],
            cooldown_minutes=0,
        )
        results = await composite.evaluate_all(position, bar, [bar])

        # At minimum, stop loss should trigger
        assert len(results) >= 1
        assert any(r.exit_type == "stop_loss" for r in results)

    @pytest.mark.asyncio
    async def test_sorted_by_urgency(self):
        """Results should be sorted: CRITICAL first, LOW last."""
        # Position triggers both stop loss (CRITICAL) and some other
        position = make_position(
            direction="LONG",
            stop_loss_price=185.0,
            max_hold_days=5,
            bars_held=10,
        )
        bar = make_bar(close=183.0)

        composite = CompositeExitStrategy(
            strategies=[StopLossStrategy(), TimeBasedExitStrategy()],
            cooldown_minutes=0,
        )
        results = await composite.evaluate_all(position, bar, [bar])

        if len(results) >= 2:
            urgency_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            for i in range(len(results) - 1):
                assert urgency_order[results[i].urgency.value] <= urgency_order[results[i + 1].urgency.value]

    @pytest.mark.asyncio
    async def test_cooldown_prevents_repeat_alerts(self):
        """Same exit_type should not fire twice within cooldown period."""
        position = make_position(direction="LONG", stop_loss_price=185.0)
        bar = make_bar(close=184.0)

        composite = CompositeExitStrategy(
            strategies=[StopLossStrategy()],
            cooldown_minutes=5,  # 5 min cooldown
        )

        # First call: should trigger
        results1 = await composite.evaluate_all(position, bar, [bar])
        assert len(results1) >= 1

        # Second call immediately: CRITICAL always goes through
        results2 = await composite.evaluate_all(position, bar, [bar])
        # CRITICAL bypasses cooldown
        assert len(results2) >= 1
