"""
Sentiment Shift Exit Strategy.

Monitors for adverse news on open positions:
- Negative headlines for LONG positions
- Positive headlines for SHORT positions

Catches things indicators can't: lawsuits, earnings warnings,
executive departures, product recalls.

Phase 1: Uses simulated sentiment engine.
Phase 3+: Will use real news API + Claude sentiment analysis.
"""

from app.engine.sentiment import get_sentiment_score
from app.models.position import Position
from app.positions.exit_strategies.base import ExitStrategy, ExitSignalResult, ExitUrgency


class SentimentShiftStrategy(ExitStrategy):
    async def evaluate(
        self, position: Position, current_bar: dict, recent_bars: list[dict]
    ) -> ExitSignalResult | None:
        sentiment = await get_sentiment_score(position.symbol)

        if not sentiment or sentiment["headline_count"] == 0:
            return None

        is_long = position.direction == "LONG"
        score = sentiment["score"]

        # Check for adverse sentiment
        if is_long and score >= -0.3:
            return None  # Sentiment is neutral or positive, no concern
        if not is_long and score <= 0.3:
            return None  # Sentiment is neutral or negative, no concern for shorts

        # Count adverse headlines
        adverse_count = (
            sentiment["negative_count"] if is_long else sentiment["positive_count"]
        )

        if adverse_count == 0:
            return None

        # Determine urgency
        if abs(score) > 0.7 or adverse_count >= 3:
            urgency = ExitUrgency.HIGH
        else:
            urgency = ExitUrgency.MEDIUM

        direction_word = "negative" if is_long else "positive"

        # Get worst headline for the message
        headlines = sentiment.get("headlines", [])
        adverse_headlines = [
            h for h in headlines
            if (is_long and h["category"] == "negative")
            or (not is_long and h["category"] == "positive")
        ]
        worst = adverse_headlines[0] if adverse_headlines else None
        worst_text = worst["headline"][:80] if worst else "Multiple adverse headlines"

        return ExitSignalResult(
            triggered=True,
            exit_type="sentiment_shift",
            urgency=urgency,
            trigger_price=None,
            current_price=current_bar["close"],
            message=(
                f"SENTIMENT SHIFT on {position.symbol} — "
                f"{adverse_count} {direction_word} headline(s). "
                f'Worst: "{worst_text}" (score: {score:.2f})'
            ),
            details={
                "sentiment_score": score,
                "adverse_count": adverse_count,
                "headline_count": sentiment["headline_count"],
                "worst_headline": worst_text,
            },
        )
