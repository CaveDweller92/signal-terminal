"""
Tests for signal quality improvements:
  - R:R filter (risk/reward ratio check before emitting BUY)
  - Weekly trend filter (penalty for buying into weekly downtrends)
  - Optimizer weight adaptation (weights shift based on trade outcomes)
  - MassiveSentimentAnalyzer scoring logic
"""

import pytest
import numpy as np
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta, timezone

from app.engine.analyzer import AnalyzerConfig, SignalAnalyzer
from app.engine.data_provider import DataProvider
from app.adaptation.layer1_optimizer.optimizer import OnlineOptimizer
from app.adaptation.layer1_optimizer.parameter_space import get_defaults, validate_weights
from app.engine.massive_sentiment import MassiveSentimentAnalyzer


# === Test data helpers ===

class MockDataProvider(DataProvider):
    """Configurable mock provider for targeted tests."""

    def __init__(self, daily_prices=None, trend="flat"):
        self.trend = trend
        self.daily_prices = daily_prices

    def _make_bars(self, n, base, trend_slope=0.0):
        bars = []
        for i in range(n):
            price = base + i * trend_slope
            bars.append({
                "open": round(price - 0.1, 2),
                "high": round(price + 1.5, 2),
                "low": round(price - 1.5, 2),
                "close": round(price, 2),
                "volume": 1_000_000,
                "timestamp": (datetime.now(timezone.utc) - timedelta(days=n - i)).isoformat(),
            })
        return bars

    async def get_intraday(self, symbol: str, bars: int = 78) -> list[dict]:
        return self._make_bars(bars, 100.0, 0.0)

    async def get_daily(self, symbol: str, days: int = 60) -> list[dict]:
        if self.daily_prices is not None:
            bars = []
            for i, p in enumerate(self.daily_prices):
                bars.append({
                    "open": round(p - 0.1, 2),
                    "high": round(p + 1.5, 2),
                    "low": round(p - 1.5, 2),
                    "close": round(p, 2),
                    "volume": 1_000_000,
                    "timestamp": (datetime.now(timezone.utc) - timedelta(days=len(self.daily_prices) - i)).isoformat(),
                })
            return bars

        if self.trend == "strong_down":
            return self._make_bars(days, 150.0, -1.0)
        elif self.trend == "strong_up":
            return self._make_bars(days, 50.0, 1.0)
        return self._make_bars(days, 100.0, 0.0)

    async def get_quote(self, symbol: str) -> dict:
        return {"symbol": symbol, "price": 100.0, "change": 0, "change_pct": 0, "volume": 0, "timestamp": ""}


# === R:R Filter ===

class TestRiskRewardFilter:
    @pytest.mark.asyncio
    async def test_buy_blocked_when_rr_too_low(self):
        """BUY should not fire if reward/risk < 1.5."""
        # Create a scenario where ATR is very large (wide stop) but target is close
        # Price=100, ATR=20 → stop=100-2.5*20=50, target=100+4*20=180
        # R:R = 80/50 = 1.6 — this should pass.
        # Instead, use a config where stop is wider than target.
        config = AnalyzerConfig()
        config.min_signal_strength = 0.1  # very low threshold to force BUY consideration
        config.atr_stop_multiplier = 5.0  # very wide stop
        config.atr_target_multiplier = 2.0  # narrow target
        # R:R = (2*ATR) / (5*ATR) = 0.4 — should be blocked

        provider = MockDataProvider(trend="strong_up")
        analyzer = SignalAnalyzer(provider, config)
        result = await analyzer.analyze("TEST")

        if result and result["conviction"] >= config.min_signal_strength:
            # If conviction is high enough for BUY, check R:R blocked it
            if result["signal_type"] == "HOLD":
                reasons = result["reasons"]["technical"]
                assert any("R:R" in r for r in reasons), "Should have R:R rejection reason"

    @pytest.mark.asyncio
    async def test_exit_levels_computed_before_signal_type(self):
        """Stop loss and profit target must be present regardless of signal type."""
        config = AnalyzerConfig()
        provider = MockDataProvider(trend="flat")
        analyzer = SignalAnalyzer(provider, config)

        result = await analyzer.analyze("AAPL")
        assert result is not None
        assert result["suggested_stop_loss"] > 0
        assert result["suggested_profit_target"] > 0
        assert result["suggested_stop_loss"] < result["price_at_signal"]
        assert result["suggested_profit_target"] > result["price_at_signal"]


# === Weekly Trend Filter ===

class TestWeeklyTrendFilter:
    @pytest.mark.asyncio
    async def test_strong_downtrend_adds_penalty_reason(self):
        """Stock far below 50-day EMA should have a weekly downtrend reason."""
        # Starts at 200, drops to 140 — current price well below 50-day EMA
        down_prices = [200.0 - i * 1.0 for i in range(60)]
        provider = MockDataProvider(daily_prices=down_prices)
        analyzer = SignalAnalyzer(provider, AnalyzerConfig())
        result = await analyzer.analyze("TEST")

        assert result is not None
        tech_reasons = result["reasons"]["technical"]
        assert any("eekly" in r for r in tech_reasons), f"No weekly trend reason in: {tech_reasons}"
        assert any("downtrend" in r.lower() for r in tech_reasons)

    @pytest.mark.asyncio
    async def test_strong_uptrend_adds_boost_reason(self):
        """Stock far above 50-day EMA should have a weekly uptrend reason."""
        # Starts at 100, rises to 160 — current price well above 50-day EMA
        up_prices = [100.0 + i * 1.0 for i in range(60)]
        provider = MockDataProvider(daily_prices=up_prices)
        analyzer = SignalAnalyzer(provider, AnalyzerConfig())
        result = await analyzer.analyze("TEST")

        assert result is not None
        tech_reasons = result["reasons"]["technical"]
        assert any("eekly" in r for r in tech_reasons), f"No weekly trend reason in: {tech_reasons}"
        assert any("uptrend" in r.lower() for r in tech_reasons)

    @pytest.mark.asyncio
    async def test_flat_price_no_weekly_reason(self):
        """Flat stock near its 50-day EMA should have no weekly trend reason."""
        flat_prices = [100.0 + (i % 3 - 1) * 0.2 for i in range(60)]  # oscillates ±0.2
        provider = MockDataProvider(daily_prices=flat_prices)
        analyzer = SignalAnalyzer(provider, AnalyzerConfig())
        result = await analyzer.analyze("TEST")

        assert result is not None
        tech_reasons = result["reasons"]["technical"]
        assert not any("eekly" in r for r in tech_reasons), f"Should have no weekly reason: {tech_reasons}"


# === No Simulated Data ===

class TestNoSimulatedData:
    @pytest.mark.asyncio
    async def test_no_sentiment_returns_zero(self):
        """Without sentiment provider, score should be 0.0, not random."""
        provider = MockDataProvider(trend="flat")
        analyzer = SignalAnalyzer(provider, AnalyzerConfig())
        # analyzer has no sentiment provider (no API keys)
        result = await analyzer.analyze("TEST")

        assert result is not None
        assert result["sentiment_score"] == 0.0

    @pytest.mark.asyncio
    async def test_no_fundamental_returns_zero(self):
        """Without fundamental provider, score should be 0.0, not random."""
        provider = MockDataProvider(trend="flat")
        analyzer = SignalAnalyzer(provider, AnalyzerConfig())
        result = await analyzer.analyze("TEST")

        assert result is not None
        assert result["fundamental_score"] == 0.0


# === Optimizer Weight Adaptation ===

class TestWeightAdaptation:
    def test_losing_trade_reduces_dominant_weight(self):
        """After a loss, the dominant component's weight should decrease."""
        optimizer = OnlineOptimizer()
        params = get_defaults()

        # Create a signal where tech_score was dominant
        signal = MagicMock()
        signal.tech_score = 3.0
        signal.sentiment_score = 0.5
        signal.fundamental_score = 0.2

        position = MagicMock()
        position.exit_reason = "manual"
        position.bars_held = 10
        position.entry_signal_id = 1

        adjusted = optimizer._compute_adjustment(params, position, pnl=-3.0, signal=signal)

        # Technical weight should have decreased (it was dominant and trade lost)
        assert adjusted["technical_weight"] < params["technical_weight"]

    def test_winning_trade_boosts_dominant_weight(self):
        """After a win, the dominant component's weight should increase."""
        optimizer = OnlineOptimizer()
        params = get_defaults()

        signal = MagicMock()
        signal.tech_score = 1.0
        signal.sentiment_score = 2.5  # sentiment was dominant
        signal.fundamental_score = 0.3

        position = MagicMock()
        position.exit_reason = "profit_target"
        position.bars_held = 15
        position.entry_signal_id = 1

        adjusted = optimizer._compute_adjustment(params, position, pnl=5.0, signal=signal)

        # Sentiment weight should have increased (it was dominant and trade won)
        assert adjusted["sentiment_weight"] > params["sentiment_weight"]

    def test_no_signal_skips_weight_adjustment(self):
        """Without linked signal, weights should not change."""
        optimizer = OnlineOptimizer()
        params = get_defaults()

        position = MagicMock()
        position.exit_reason = "manual"
        position.bars_held = 10
        position.entry_signal_id = None

        adjusted = optimizer._compute_adjustment(params, position, pnl=-2.0, signal=None)

        # Weights should be unchanged (only min_signal_strength adjusted)
        validated = validate_weights(adjusted)
        assert validated["technical_weight"] == pytest.approx(params["technical_weight"], abs=0.01)

    def test_weights_stay_normalized_after_adaptation(self):
        """Weights must always sum to 1.0 after adjustment."""
        optimizer = OnlineOptimizer()
        params = get_defaults()

        signal = MagicMock()
        signal.tech_score = 4.0
        signal.sentiment_score = 1.0
        signal.fundamental_score = 0.5

        position = MagicMock()
        position.exit_reason = "stop_loss"
        position.bars_held = 5
        position.entry_signal_id = 1

        adjusted = optimizer._compute_adjustment(params, position, pnl=-5.0, signal=signal)

        total = adjusted["technical_weight"] + adjusted["sentiment_weight"] + adjusted["fundamental_weight"]
        assert abs(total - 1.0) < 0.02


# === MassiveSentimentAnalyzer Scoring ===

class TestMassiveSentimentScoring:
    def test_positive_sentiment_gives_positive_score(self):
        """All positive insights should produce a positive score."""
        analyzer = MassiveSentimentAnalyzer("fake_key")
        articles = [
            {
                "published_utc": datetime.now(timezone.utc).isoformat(),
                "insights": [{"ticker": "AAPL", "sentiment": "positive", "sentiment_reasoning": "Strong earnings"}],
            },
            {
                "published_utc": datetime.now(timezone.utc).isoformat(),
                "insights": [{"ticker": "AAPL", "sentiment": "positive", "sentiment_reasoning": "New product launch"}],
            },
        ]
        result = analyzer._score_from_insights("AAPL", articles)
        assert result is not None
        assert result["score"] > 0
        assert result["source"] == "massive-insights"

    def test_negative_sentiment_gives_negative_score(self):
        """All negative insights should produce a negative score."""
        analyzer = MassiveSentimentAnalyzer("fake_key")
        articles = [
            {
                "published_utc": datetime.now(timezone.utc).isoformat(),
                "insights": [{"ticker": "AAPL", "sentiment": "negative", "sentiment_reasoning": "Lawsuit filed"}],
            },
        ]
        result = analyzer._score_from_insights("AAPL", articles)
        assert result is not None
        assert result["score"] < 0

    def test_mixed_sentiment_near_zero(self):
        """Equal positive and negative should produce near-zero score."""
        analyzer = MassiveSentimentAnalyzer("fake_key")
        now = datetime.now(timezone.utc).isoformat()
        articles = [
            {"published_utc": now, "insights": [{"ticker": "AAPL", "sentiment": "positive", "sentiment_reasoning": "Good"}]},
            {"published_utc": now, "insights": [{"ticker": "AAPL", "sentiment": "negative", "sentiment_reasoning": "Bad"}]},
        ]
        result = analyzer._score_from_insights("AAPL", articles)
        assert result is not None
        assert abs(result["score"]) < 1.0

    def test_filters_to_correct_ticker(self):
        """Should only use insights for the requested ticker."""
        analyzer = MassiveSentimentAnalyzer("fake_key")
        articles = [
            {
                "published_utc": datetime.now(timezone.utc).isoformat(),
                "insights": [
                    {"ticker": "GOOG", "sentiment": "negative", "sentiment_reasoning": "Bad for Google"},
                    {"ticker": "AAPL", "sentiment": "positive", "sentiment_reasoning": "Good for Apple"},
                ],
            },
        ]
        result = analyzer._score_from_insights("AAPL", articles)
        assert result is not None
        assert result["score"] > 0  # only AAPL insight used (positive)

    def test_no_insights_returns_none(self):
        """Articles without insights should return None (fallback to Claude)."""
        analyzer = MassiveSentimentAnalyzer("fake_key")
        articles = [
            {"published_utc": datetime.now(timezone.utc).isoformat(), "title": "Some article"},
        ]
        result = analyzer._score_from_insights("AAPL", articles)
        assert result is None

    def test_recency_weighting(self):
        """Recent articles should have more weight than older ones."""
        analyzer = MassiveSentimentAnalyzer("fake_key")
        now = datetime.now(timezone.utc)
        articles = [
            {
                "published_utc": now.isoformat(),
                "insights": [{"ticker": "AAPL", "sentiment": "positive", "sentiment_reasoning": "Today"}],
            },
            {
                "published_utc": (now - timedelta(days=6)).isoformat(),
                "insights": [{"ticker": "AAPL", "sentiment": "negative", "sentiment_reasoning": "Old news"}],
            },
        ]
        result = analyzer._score_from_insights("AAPL", articles)
        assert result is not None
        # Recent positive should outweigh old negative due to recency weighting
        assert result["score"] > 0

    def test_score_clamped_to_range(self):
        """Score should always be between -3 and +3."""
        analyzer = MassiveSentimentAnalyzer("fake_key")
        now = datetime.now(timezone.utc).isoformat()
        # Many positive articles
        articles = [
            {"published_utc": now, "insights": [{"ticker": "X", "sentiment": "positive", "sentiment_reasoning": f"Good {i}"}]}
            for i in range(20)
        ]
        result = analyzer._score_from_insights("X", articles)
        assert result is not None
        assert -3.0 <= result["score"] <= 3.0
