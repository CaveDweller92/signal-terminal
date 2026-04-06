"""
Sentiment Shift Exit Strategy.

Monitors for adverse sentiment on open positions using real news data:
- Negative sentiment for LONG positions
- Positive sentiment for SHORT positions

Uses the same sentiment providers as the signal analyzer:
  US stocks → MassiveSentimentAnalyzer (Massive news API + built-in insights)
  .TO stocks → SentimentAnalyzer (Finnhub + Claude)

Catches things indicators can't: lawsuits, earnings warnings,
executive departures, product recalls.
"""

import logging

from app.models.position import Position
from app.positions.exit_strategies.base import ExitStrategy, ExitSignalResult, ExitUrgency

logger = logging.getLogger(__name__)


class SentimentShiftStrategy(ExitStrategy):
    async def evaluate(
        self, position: Position, current_bar: dict, recent_bars: list[dict]
    ) -> ExitSignalResult | None:
        # Get the real sentiment provider (same singletons as analyzer)
        from app.engine.analyzer import _get_massive_sentiment, _get_finnhub_sentiment

        is_tsx = position.symbol.endswith(".TO")
        provider = _get_finnhub_sentiment() if is_tsx else _get_massive_sentiment()

        if provider is None:
            return None

        try:
            sentiment = await provider.get_sentiment(position.symbol)
        except Exception as e:
            logger.debug("SentimentShift: failed to fetch for %s: %s", position.symbol, e)
            return None

        score = sentiment.get("score", 0.0)
        reasons = sentiment.get("reasons", [])
        source = sentiment.get("source", "unknown")

        # No data or neutral — no concern
        if source in ("none", "error") or abs(score) < 0.5:
            return None

        is_long = position.direction == "LONG"

        # Check for adverse sentiment
        if is_long and score >= -0.5:
            return None  # Sentiment is neutral or positive — no concern
        if not is_long and score <= 0.5:
            return None  # Sentiment is neutral or negative — no concern for shorts

        # Determine urgency based on severity
        if abs(score) >= 2.0:
            urgency = ExitUrgency.HIGH
        else:
            urgency = ExitUrgency.MEDIUM

        direction_word = "negative" if is_long else "positive"
        worst_reason = reasons[0][:80] if reasons else "Adverse sentiment detected"

        return ExitSignalResult(
            triggered=True,
            exit_type="sentiment_shift",
            urgency=urgency,
            trigger_price=None,
            current_price=current_bar["close"],
            message=(
                f"SENTIMENT SHIFT on {position.symbol} — "
                f"{direction_word} sentiment (score: {score:+.1f}). "
                f'"{worst_reason}"'
            ),
            details={
                "sentiment_score": score,
                "reasons": reasons[:3],
                "source": source,
            },
        )
