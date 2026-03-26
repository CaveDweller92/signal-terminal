"""
Tests for engine/indicators.py — the math must be correct.

These are the foundation of every signal. If RSI or EMA is wrong,
everything downstream (analyzer, exit strategies) is wrong.
"""

import numpy as np
import pytest

from app.engine.indicators import (
    calc_atr,
    calc_ema,
    calc_macd,
    calc_rsi,
    calc_volume_ratio,
    detect_ema_crossover,
)


# --- EMA ---

class TestEMA:
    def test_ema_returns_correct_length(self):
        closes = np.array([10.0, 11.0, 12.0, 13.0, 14.0, 15.0])
        result = calc_ema(closes, period=3)
        assert len(result) == len(closes)

    def test_ema_seed_is_sma(self):
        """First valid EMA value should equal the SMA of the first N values."""
        closes = np.array([10.0, 12.0, 14.0, 13.0, 15.0])
        result = calc_ema(closes, period=3)
        expected_seed = np.mean([10.0, 12.0, 14.0])  # 12.0
        assert result[2] == pytest.approx(expected_seed)

    def test_ema_early_values_are_nan(self):
        closes = np.array([10.0, 11.0, 12.0, 13.0, 14.0])
        result = calc_ema(closes, period=3)
        assert np.isnan(result[0])
        assert np.isnan(result[1])
        assert not np.isnan(result[2])

    def test_ema_too_short_returns_all_nan(self):
        closes = np.array([10.0, 11.0])
        result = calc_ema(closes, period=5)
        assert all(np.isnan(result))

    def test_ema_reacts_to_price_increase(self):
        """EMA should trend upward when prices rise."""
        closes = np.array([10.0] * 10 + [15.0] * 5)
        result = calc_ema(closes, period=5)
        # Later values should be higher than earlier
        valid = result[~np.isnan(result)]
        assert valid[-1] > valid[5]

    def test_fast_ema_reacts_faster_than_slow(self):
        """Shorter period EMA should respond more quickly to a price jump."""
        closes = np.array([100.0] * 30 + [110.0] * 5)
        fast = calc_ema(closes, period=5)
        slow = calc_ema(closes, period=20)
        # After the jump, fast EMA should be closer to 110 than slow
        assert fast[-1] > slow[-1]


# --- RSI ---

class TestRSI:
    def test_rsi_range(self):
        """RSI must always be between 0 and 100."""
        closes = np.random.default_rng(42).normal(100, 5, size=50)
        result = calc_rsi(closes)
        valid = result[~np.isnan(result)]
        assert all(0 <= v <= 100 for v in valid)

    def test_rsi_overbought_on_pure_gains(self):
        """Monotonically rising prices should produce RSI near 100."""
        closes = np.arange(50, 100, dtype=float)
        result = calc_rsi(closes, period=14)
        valid = result[~np.isnan(result)]
        assert valid[-1] > 90

    def test_rsi_oversold_on_pure_losses(self):
        """Monotonically falling prices should produce RSI near 0."""
        closes = np.arange(100, 50, -1, dtype=float)
        result = calc_rsi(closes, period=14)
        valid = result[~np.isnan(result)]
        assert valid[-1] < 10

    def test_rsi_around_50_on_flat(self):
        """Flat prices should give RSI around 50."""
        closes = np.full(30, 100.0)
        # Add tiny noise to avoid division by zero
        closes += np.random.default_rng(42).normal(0, 0.01, size=30)
        result = calc_rsi(closes, period=14)
        valid = result[~np.isnan(result)]
        assert 30 < valid[-1] < 70

    def test_rsi_too_short_returns_nan(self):
        closes = np.array([10.0, 11.0, 12.0])
        result = calc_rsi(closes, period=14)
        assert all(np.isnan(result))


# --- MACD ---

class TestMACD:
    def test_macd_returns_three_arrays(self):
        closes = np.random.default_rng(42).normal(100, 5, size=50)
        macd_line, signal_line, histogram = calc_macd(closes)
        assert len(macd_line) == len(closes)
        assert len(signal_line) == len(closes)
        assert len(histogram) == len(closes)

    def test_histogram_is_macd_minus_signal(self):
        closes = np.random.default_rng(42).normal(100, 5, size=60)
        macd_line, signal_line, histogram = calc_macd(closes)
        # Where both are valid, histogram = macd - signal
        for i in range(len(closes)):
            if not np.isnan(macd_line[i]) and not np.isnan(signal_line[i]):
                assert histogram[i] == pytest.approx(macd_line[i] - signal_line[i])

    def test_macd_bullish_on_uptrend(self):
        """In a strong uptrend, MACD line should be positive."""
        closes = np.linspace(80, 120, 60)
        macd_line, _, _ = calc_macd(closes)
        valid = macd_line[~np.isnan(macd_line)]
        assert valid[-1] > 0


# --- ATR ---

class TestATR:
    def test_atr_positive(self):
        """ATR should always be positive."""
        rng = np.random.default_rng(42)
        closes = 100 + np.cumsum(rng.normal(0, 1, size=30))
        highs = closes + abs(rng.normal(1, 0.5, size=30))
        lows = closes - abs(rng.normal(1, 0.5, size=30))
        result = calc_atr(highs, lows, closes)
        valid = result[~np.isnan(result)]
        assert all(v > 0 for v in valid)

    def test_atr_higher_for_volatile_stock(self):
        """More volatile data should produce higher ATR."""
        rng = np.random.default_rng(42)
        # Calm stock
        calm_closes = 100 + np.cumsum(rng.normal(0, 0.5, size=30))
        calm_highs = calm_closes + 0.5
        calm_lows = calm_closes - 0.5
        calm_atr = calc_atr(calm_highs, calm_lows, calm_closes)

        # Volatile stock
        vol_closes = 100 + np.cumsum(rng.normal(0, 3, size=30))
        vol_highs = vol_closes + 3
        vol_lows = vol_closes - 3
        vol_atr = calc_atr(vol_highs, vol_lows, vol_closes)

        calm_valid = calm_atr[~np.isnan(calm_atr)]
        vol_valid = vol_atr[~np.isnan(vol_atr)]
        assert vol_valid[-1] > calm_valid[-1]


# --- Volume Ratio ---

class TestVolumeRatio:
    def test_volume_ratio_normal_is_around_one(self):
        """Consistent volume should give ratio around 1.0."""
        volumes = np.full(30, 1_000_000.0)
        result = calc_volume_ratio(volumes, period=20)
        valid = result[~np.isnan(result)]
        assert all(abs(v - 1.0) < 0.01 for v in valid)

    def test_volume_spike_detected(self):
        """A volume spike should produce ratio > 2."""
        volumes = np.full(25, 1_000_000.0)
        volumes[-1] = 3_000_000.0  # 3x spike
        result = calc_volume_ratio(volumes, period=20)
        assert result[-1] > 2.5


# --- EMA Crossover ---

class TestEMACrossover:
    def test_bullish_crossover(self):
        """Fast EMA above slow = bullish."""
        # Uptrend: fast EMA will be above slow
        closes = np.linspace(80, 120, 40)
        result = detect_ema_crossover(closes, fast_period=5, slow_period=20)
        assert result["crossover"] == "bullish"

    def test_bearish_crossover(self):
        """Fast EMA below slow = bearish."""
        closes = np.linspace(120, 80, 40)
        result = detect_ema_crossover(closes, fast_period=5, slow_period=20)
        assert result["crossover"] == "bearish"

    def test_returns_required_keys(self):
        closes = np.linspace(80, 120, 40)
        result = detect_ema_crossover(closes)
        assert "crossover" in result
        assert "just_crossed" in result
        assert "ema_fast" in result
        assert "ema_slow" in result
        assert "spread" in result
