"""
Tests for engine/analyzer.py — conviction scoring and signal generation.

The analyzer takes indicator output and produces BUY/SELL/HOLD decisions.
If scoring or thresholds are wrong, the user gets bad signals.
"""

import pytest

from app.engine.analyzer import AnalyzerConfig, SignalAnalyzer
from app.engine.data_provider import SimulatedDataProvider


@pytest.fixture
def analyzer():
    provider = SimulatedDataProvider()
    return SignalAnalyzer(provider)


@pytest.fixture
def config():
    return AnalyzerConfig()


class TestAnalyzerConfig:
    def test_default_weights_sum_to_one(self, config):
        total = config.technical_weight + config.sentiment_weight + config.fundamental_weight
        assert total == pytest.approx(1.0)

    def test_default_rsi_bounds(self, config):
        assert config.rsi_oversold < config.rsi_overbought
        assert 0 < config.rsi_oversold < 50
        assert 50 < config.rsi_overbought < 100


class TestSignalAnalyzer:
    @pytest.mark.asyncio
    async def test_analyze_returns_required_fields(self, analyzer):
        result = await analyzer.analyze("AAPL")
        required = [
            "symbol", "signal_type", "conviction", "tech_score",
            "sentiment_score", "fundamental_score", "price_at_signal",
            "suggested_stop_loss", "suggested_profit_target",
            "atr_at_signal", "reasons", "indicators",
        ]
        for field in required:
            assert field in result, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_signal_type_is_valid(self, analyzer):
        result = await analyzer.analyze("AAPL")
        assert result["signal_type"] in ("BUY", "SELL", "HOLD")

    @pytest.mark.asyncio
    async def test_conviction_is_float(self, analyzer):
        result = await analyzer.analyze("MSFT")
        assert isinstance(result["conviction"], float)

    @pytest.mark.asyncio
    async def test_stop_loss_below_price_for_long(self, analyzer):
        """Suggested stop loss should be below entry price (for long context)."""
        result = await analyzer.analyze("AAPL")
        assert result["suggested_stop_loss"] < result["price_at_signal"]

    @pytest.mark.asyncio
    async def test_profit_target_above_price(self, analyzer):
        """Suggested profit target should be above entry price."""
        result = await analyzer.analyze("AAPL")
        assert result["suggested_profit_target"] > result["price_at_signal"]

    @pytest.mark.asyncio
    async def test_atr_is_positive(self, analyzer):
        result = await analyzer.analyze("NVDA")
        assert result["atr_at_signal"] > 0

    @pytest.mark.asyncio
    async def test_reasons_has_three_dimensions(self, analyzer):
        result = await analyzer.analyze("TSLA")
        reasons = result["reasons"]
        assert "technical" in reasons
        assert "sentiment" in reasons
        assert "fundamental" in reasons

    @pytest.mark.asyncio
    async def test_indicators_present(self, analyzer):
        result = await analyzer.analyze("GOOGL")
        indicators = result["indicators"]
        assert "rsi" in indicators
        assert "macd_histogram" in indicators
        assert "ema_crossover" in indicators
        assert "volume_ratio" in indicators

    @pytest.mark.asyncio
    async def test_different_symbols_produce_different_results(self, analyzer):
        r1 = await analyzer.analyze("AAPL")
        r2 = await analyzer.analyze("TSLA")
        # Different symbols should have different prices at minimum
        assert r1["price_at_signal"] != r2["price_at_signal"]

    @pytest.mark.asyncio
    async def test_buy_signal_has_positive_conviction(self, analyzer):
        """If signal is BUY, conviction must be positive."""
        # Test across multiple symbols to find a BUY
        for symbol in ["AAPL", "MSFT", "NVDA", "AMD", "GOOGL", "TSLA", "META", "NFLX"]:
            result = await analyzer.analyze(symbol)
            if result["signal_type"] == "BUY":
                assert result["conviction"] > 0
                return
        # If no BUY found, that's ok — the test is about correctness when it happens

    @pytest.mark.asyncio
    async def test_sell_signal_has_negative_conviction(self, analyzer):
        """If signal is SELL, conviction must be negative."""
        for symbol in ["AAPL", "MSFT", "NVDA", "AMD", "GOOGL", "TSLA", "META", "NFLX"]:
            result = await analyzer.analyze(symbol)
            if result["signal_type"] == "SELL":
                assert result["conviction"] < 0
                return


class TestTechnicalScoring:
    def test_rsi_oversold_gives_positive_score(self, analyzer):
        score, reasons = analyzer._score_technical(
            rsi=25.0, macd_hist=0.0, crossover={"crossover": "none", "just_crossed": False}, vol_ratio=1.0
        )
        assert score > 0
        assert any("oversold" in r.lower() for r in reasons)

    def test_rsi_overbought_gives_negative_score(self, analyzer):
        score, reasons = analyzer._score_technical(
            rsi=75.0, macd_hist=0.0, crossover={"crossover": "none", "just_crossed": False}, vol_ratio=1.0
        )
        assert score < 0
        assert any("overbought" in r.lower() for r in reasons)

    def test_bullish_crossover_adds_to_score(self, analyzer):
        score_no_cross, _ = analyzer._score_technical(
            rsi=50.0, macd_hist=0.0, crossover={"crossover": "none", "just_crossed": False}, vol_ratio=1.0
        )
        score_cross, _ = analyzer._score_technical(
            rsi=50.0, macd_hist=0.0, crossover={"crossover": "bullish", "just_crossed": True}, vol_ratio=1.0
        )
        assert score_cross > score_no_cross

    def test_volume_spike_amplifies_signal(self, analyzer):
        score_normal, _ = analyzer._score_technical(
            rsi=25.0, macd_hist=0.01, crossover={"crossover": "bullish", "just_crossed": False}, vol_ratio=1.0
        )
        score_spike, _ = analyzer._score_technical(
            rsi=25.0, macd_hist=0.01, crossover={"crossover": "bullish", "just_crossed": False}, vol_ratio=2.5
        )
        assert abs(score_spike) > abs(score_normal)

    def test_low_volume_discounts_signal(self, analyzer):
        score_normal, _ = analyzer._score_technical(
            rsi=25.0, macd_hist=0.01, crossover={"crossover": "bullish", "just_crossed": False}, vol_ratio=1.0
        )
        score_low_vol, _ = analyzer._score_technical(
            rsi=25.0, macd_hist=0.01, crossover={"crossover": "bullish", "just_crossed": False}, vol_ratio=0.3
        )
        assert abs(score_low_vol) < abs(score_normal)

    def test_score_clamped_to_range(self, analyzer):
        """Score should never exceed -5 to +5."""
        score, _ = analyzer._score_technical(
            rsi=15.0, macd_hist=0.1, crossover={"crossover": "bullish", "just_crossed": True}, vol_ratio=3.0
        )
        assert -5.0 <= score <= 5.0
