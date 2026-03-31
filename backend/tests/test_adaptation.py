"""
Tests for adaptation layer — optimizer, regime presets, parameter space.

The adaptation layer modifies strategy parameters. If it breaks,
parameters could drift to extreme values and generate bad signals.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.adaptation.layer1_optimizer.parameter_space import (
    PARAMETER_SPACE,
    PARAM_BOUNDS,
    clamp_params,
    get_defaults,
    validate_weights,
)
from app.adaptation.layer1_optimizer.optimizer import OnlineOptimizer
from app.adaptation.layer2_regime.presets import REGIME_PRESETS, get_preset


# === Parameter Space ===

class TestParameterSpace:
    def test_all_params_have_valid_bounds(self):
        for p in PARAMETER_SPACE:
            assert p.min_val < p.max_val, f"{p.name}: min >= max"
            assert p.min_val <= p.default <= p.max_val, f"{p.name}: default out of bounds"
            assert p.step > 0, f"{p.name}: step must be positive"

    def test_defaults_returns_all_params(self):
        defaults = get_defaults()
        for p in PARAMETER_SPACE:
            assert p.name in defaults, f"Missing default for {p.name}"
            assert defaults[p.name] == p.default

    def test_clamp_respects_bounds(self):
        params = {
            "rsi_period": 100,  # Max is 30
            "rsi_oversold": -5,  # Min is 10
            "ema_fast": 15,  # Within bounds
        }
        clamped = clamp_params(params)
        assert clamped["rsi_period"] == 30
        assert clamped["rsi_oversold"] == 10
        assert clamped["ema_fast"] == 15

    def test_clamp_passes_unknown_params(self):
        params = {"unknown_param": 42}
        clamped = clamp_params(params)
        assert clamped["unknown_param"] == 42

    def test_validate_weights_normalizes(self):
        params = {
            "technical_weight": 0.6,
            "sentiment_weight": 0.6,
            "fundamental_weight": 0.6,
        }
        validated = validate_weights(params)
        total = (
            validated["technical_weight"]
            + validated["sentiment_weight"]
            + validated["fundamental_weight"]
        )
        assert abs(total - 1.0) < 0.01

    def test_validate_weights_preserves_valid(self):
        params = {
            "technical_weight": 0.5,
            "sentiment_weight": 0.3,
            "fundamental_weight": 0.2,
        }
        validated = validate_weights(params)
        assert validated["technical_weight"] == 0.5
        assert validated["sentiment_weight"] == 0.3
        assert validated["fundamental_weight"] == 0.2

    def test_default_weights_sum_to_one(self):
        defaults = get_defaults()
        total = (
            defaults["technical_weight"]
            + defaults["sentiment_weight"]
            + defaults["fundamental_weight"]
        )
        assert abs(total - 1.0) < 0.01


# === Regime Presets ===

class TestRegimePresets:
    def test_all_regimes_have_presets(self):
        expected_regimes = [
            "trending_up", "trending_down", "mean_reverting",
            "volatile_choppy", "low_volatility",
        ]
        for regime in expected_regimes:
            assert regime in REGIME_PRESETS, f"Missing preset for {regime}"

    def test_presets_have_exit_params(self):
        """Every preset should include exit parameters."""
        for regime, preset in REGIME_PRESETS.items():
            assert "atr_target_multiplier" in preset, f"{regime}: missing atr_target_multiplier"
            assert "atr_stop_multiplier" in preset, f"{regime}: missing atr_stop_multiplier"
            assert "max_hold_days" in preset, f"{regime}: missing max_hold_days"

    def test_preset_values_within_bounds(self):
        """Preset values should be within parameter space bounds."""
        for regime, preset in REGIME_PRESETS.items():
            for key, value in preset.items():
                if key in PARAM_BOUNDS:
                    bound = PARAM_BOUNDS[key]
                    assert bound.min_val <= value <= bound.max_val, (
                        f"{regime}.{key} = {value} outside [{bound.min_val}, {bound.max_val}]"
                    )

    def test_volatile_choppy_has_tightest_stops(self):
        """In choppy markets, stops should be tightest."""
        choppy = REGIME_PRESETS["volatile_choppy"]
        trend_up = REGIME_PRESETS["trending_up"]
        assert choppy["atr_stop_multiplier"] < trend_up["atr_stop_multiplier"]
        assert choppy["max_hold_days"] < trend_up["max_hold_days"]

    def test_trending_up_has_widest_targets(self):
        """In uptrends, targets should be widest (let winners run)."""
        trend_up = REGIME_PRESETS["trending_up"]
        for regime, preset in REGIME_PRESETS.items():
            if regime != "trending_up":
                assert trend_up["atr_target_multiplier"] >= preset["atr_target_multiplier"], (
                    f"trending_up target ({trend_up['atr_target_multiplier']}) "
                    f"should be >= {regime} target ({preset['atr_target_multiplier']})"
                )

    def test_get_preset_unknown_returns_empty(self):
        assert get_preset("nonexistent_regime") == {}

    def test_get_preset_returns_copy(self):
        """get_preset should return a copy, not a reference."""
        preset = get_preset("trending_up")
        preset["atr_stop_multiplier"] = 999
        assert REGIME_PRESETS["trending_up"]["atr_stop_multiplier"] != 999


# === Online Optimizer ===

class TestOnlineOptimizer:
    @pytest.mark.asyncio
    async def test_skip_non_closed_position(self):
        optimizer = OnlineOptimizer()
        db = AsyncMock()
        position = MagicMock()
        position.status = "OPEN"
        position.realized_pnl_pct = None

        result = await optimizer.update_after_trade(db, position)
        assert result is None

    @pytest.mark.asyncio
    async def test_adjusts_after_stop_loss(self):
        optimizer = OnlineOptimizer()
        db = AsyncMock()

        # Mock no existing snapshot
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)

        position = MagicMock()
        position.status = "CLOSED"
        position.id = 1
        position.realized_pnl_pct = -2.5
        position.exit_reason = "stop_loss"
        position.bars_held = 15

        result = await optimizer.update_after_trade(db, position)
        # Should create a new snapshot with adjusted params
        assert result is not None or db.add.called

    def test_compute_adjustment_widens_stops_on_loss(self):
        optimizer = OnlineOptimizer()
        from app.adaptation.layer1_optimizer.parameter_space import get_defaults

        params = get_defaults()
        position = MagicMock()
        position.exit_reason = "stop_loss"
        position.bars_held = 20

        adjusted = optimizer._compute_adjustment(params, position, pnl=-2.0)

        # After a stop loss, stops should be slightly wider
        assert adjusted["atr_stop_multiplier"] >= params["atr_stop_multiplier"]

    def test_compute_adjustment_raises_threshold_on_loss(self):
        optimizer = OnlineOptimizer()
        from app.adaptation.layer1_optimizer.parameter_space import get_defaults

        params = get_defaults()
        position = MagicMock()
        position.exit_reason = "manual"
        position.bars_held = 30

        adjusted = optimizer._compute_adjustment(params, position, pnl=-1.5)

        # After a loss, signal threshold should increase
        assert adjusted["min_signal_strength"] >= params["min_signal_strength"]

    def test_compute_adjustment_lowers_threshold_on_win(self):
        optimizer = OnlineOptimizer()
        from app.adaptation.layer1_optimizer.parameter_space import get_defaults

        params = get_defaults()
        position = MagicMock()
        position.exit_reason = "profit_target"
        position.bars_held = 25

        adjusted = optimizer._compute_adjustment(params, position, pnl=3.0)

        # After a win, threshold should decrease slightly
        assert adjusted["min_signal_strength"] <= params["min_signal_strength"]

    def test_learning_rate_decays(self):
        optimizer = OnlineOptimizer(learning_rate=0.05, decay=0.99)
        from app.adaptation.layer1_optimizer.parameter_space import get_defaults

        params = get_defaults()
        position = MagicMock()
        position.exit_reason = "manual"
        position.bars_held = 20

        # First adjustment
        adj1 = optimizer._compute_adjustment(params, position, pnl=-2.0)
        diff1 = abs(adj1["min_signal_strength"] - params["min_signal_strength"])

        # Simulate many trades
        optimizer._trade_count = 100
        adj2 = optimizer._compute_adjustment(params, position, pnl=-2.0)
        diff2 = abs(adj2["min_signal_strength"] - params["min_signal_strength"])

        # Later adjustments should be smaller (learning rate decayed)
        assert diff2 < diff1
