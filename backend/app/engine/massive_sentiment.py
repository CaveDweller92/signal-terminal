"""
Sentiment analysis using Massive.com Ticker News API.

The /v2/reference/news endpoint returns articles with built-in per-ticker
sentiment in the `insights` array:

  {"ticker": "AAPL", "sentiment": "positive", "sentiment_reasoning": "..."}

Flow:
  1. Fetch last 7 days of news from Massive /v2/reference/news
  2. Extract built-in sentiment from insights array
  3. Weight by recency, average to -3..+3 scale
  4. If no insights available, fall back to headline extraction + Claude scoring

Caches results for 30 minutes.
Falls back to 0.0 (neutral) if API is unavailable.
"""

import json
import logging
import math
from datetime import datetime, timedelta, timezone

import httpx
from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)

_MASSIVE_BASE = "https://api.massive.com"
_CACHE_TTL = 30 * 60  # 30 minutes

# Sentiment string → numeric value
_SENTIMENT_MAP = {
    "positive": 1.0,
    "negative": -1.0,
    "neutral": 0.0,
    "bullish": 1.0,
    "bearish": -1.0,
}


class MassiveSentimentAnalyzer:
    def __init__(self, massive_api_key: str, anthropic_api_key: str = ""):
        self._massive_key = massive_api_key
        self._cache: dict[str, tuple[float, dict]] = {}
        self._client = httpx.AsyncClient(timeout=15.0)
        self._anthropic = AsyncAnthropic(api_key=anthropic_api_key) if anthropic_api_key else None

    def _cached(self, symbol: str) -> dict | None:
        if symbol in self._cache:
            fetched_at, data = self._cache[symbol]
            if datetime.now(timezone.utc).timestamp() - fetched_at < _CACHE_TTL:
                return data
        return None

    def _store(self, symbol: str, data: dict) -> None:
        self._cache[symbol] = (datetime.now(timezone.utc).timestamp(), data)

    async def get_sentiment(self, symbol: str) -> dict:
        """
        Returns:
            {score: float (-3 to +3), reasons: list[str], source: str}
        """
        cached = self._cached(symbol)
        if cached is not None:
            return cached

        articles = await self._fetch_news(symbol)
        if not articles:
            result = {"score": 0.0, "reasons": ["No recent news found"], "source": "none"}
            self._store(symbol, result)
            return result

        # Try built-in sentiment from insights
        result = self._score_from_insights(symbol, articles)
        if result is not None:
            self._store(symbol, result)
            return result

        # Fallback: extract headlines and score with Claude
        headlines = [a.get("title", "").strip() for a in articles if a.get("title")]
        if headlines and self._anthropic:
            result = await self._score_with_claude(symbol, headlines[:10])
            self._store(symbol, result)
            return result

        result = {"score": 0.0, "reasons": ["News found but no sentiment data"], "source": "massive-no-insights"}
        self._store(symbol, result)
        return result

    async def _fetch_news(self, symbol: str) -> list[dict]:
        """Fetch recent news articles from Massive /v2/reference/news."""
        from_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")

        url = (
            f"{_MASSIVE_BASE}/v2/reference/news"
            f"?ticker={symbol}"
            f"&published_utc.gte={from_date}"
            f"&limit=10"
            f"&sort=published_utc"
            f"&order=desc"
            f"&apiKey={self._massive_key}"
        )
        try:
            resp = await self._client.get(url)
            resp.raise_for_status()
            data = resp.json()
            return data.get("results", [])
        except Exception as e:
            logger.warning("MassiveSentimentAnalyzer: news fetch failed for %s: %s", symbol, e)
            return []

    def _score_from_insights(self, symbol: str, articles: list[dict]) -> dict | None:
        """
        Extract sentiment from Massive's built-in insights array.
        Each article may have insights for multiple tickers — filter to ours.
        Weight by recency: exponential decay over 7 days.
        """
        now = datetime.now(timezone.utc)
        weighted_scores: list[tuple[float, float]] = []  # (score, weight)
        reasons: list[str] = []

        for article in articles:
            insights = article.get("insights", [])
            if not insights:
                continue

            # Find insight for our ticker
            for insight in insights:
                if insight.get("ticker", "").upper() != symbol.upper():
                    continue

                sentiment_str = insight.get("sentiment", "").lower()
                numeric = _SENTIMENT_MAP.get(sentiment_str)
                if numeric is None:
                    continue

                # Recency weight: e^(-0.15 * days_old)  →  1.0 at day 0, ~0.35 at day 7
                published = article.get("published_utc", "")
                try:
                    pub_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                    days_old = (now - pub_dt).total_seconds() / 86400
                except (ValueError, TypeError):
                    days_old = 3.5  # assume mid-range if unparseable

                weight = math.exp(-0.15 * days_old)
                weighted_scores.append((numeric, weight))

                reasoning = insight.get("sentiment_reasoning", "")
                if reasoning and len(reasons) < 3:
                    reasons.append(reasoning)

        if not weighted_scores:
            return None

        # Weighted average, then scale to -3..+3
        total_weight = sum(w for _, w in weighted_scores)
        if total_weight == 0:
            return None

        raw_avg = sum(s * w for s, w in weighted_scores) / total_weight
        # raw_avg is in [-1, +1], scale to [-3, +3]
        score = round(raw_avg * 3.0, 2)
        score = max(-3.0, min(3.0, score))

        if not reasons:
            if score > 0:
                reasons = ["Positive news sentiment"]
            elif score < 0:
                reasons = ["Negative news sentiment"]
            else:
                reasons = ["Neutral news sentiment"]

        return {"score": score, "reasons": reasons, "source": "massive-insights"}

    async def _score_with_claude(self, symbol: str, headlines: list[str]) -> dict:
        """Fallback: send headlines to Claude Haiku for sentiment scoring."""
        headlines_text = "\n".join(f"- {h}" for h in headlines)

        prompt = f"""You are a financial sentiment analyst. Score the market sentiment for {symbol} based on these recent news headlines.

Headlines:
{headlines_text}

Respond with a JSON object only (no markdown, no explanation outside JSON):
{{
  "score": <float from -3.0 (very bearish) to +3.0 (very bullish)>,
  "reasons": [<1-3 brief strings explaining the score>]
}}

Guidelines:
- +3: Major positive catalyst (earnings beat, acquisition at premium, FDA approval)
- +1 to +2: Moderately positive (product launch, analyst upgrade, solid guidance)
- 0: Neutral or mixed news
- -1 to -2: Moderately negative (analyst downgrade, missed estimates, competition)
- -3: Major negative catalyst (fraud allegations, bankruptcy, major recall)"""

        try:
            message = await self._anthropic.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
            )
            content = message.content[0].text.strip()

            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
                if content.endswith("```"):
                    content = content[:-3].strip()

            parsed = json.loads(content)
            score = float(parsed.get("score", 0.0))
            score = max(-3.0, min(3.0, score))
            reasons = parsed.get("reasons", [])
            if not isinstance(reasons, list):
                reasons = [str(reasons)]

            return {"score": round(score, 2), "reasons": reasons, "source": "massive+claude"}

        except json.JSONDecodeError as e:
            logger.warning("MassiveSentimentAnalyzer: Claude returned non-JSON for %s: %s", symbol, e)
            return {"score": 0.0, "reasons": ["Sentiment parsing failed"], "source": "error"}
        except Exception as e:
            logger.warning("MassiveSentimentAnalyzer: Claude API error for %s: %s", symbol, e)
            return {"score": 0.0, "reasons": ["Sentiment API unavailable"], "source": "error"}
