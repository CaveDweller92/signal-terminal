"""
Real sentiment analysis using Finnhub company news + Claude API scoring.

Flow:
  1. Fetch last 7 days of news headlines from Finnhub /company-news (free)
  2. Send up to 10 headlines to Claude claude-haiku-4-5-20251001 for fast/cheap scoring
  3. Claude returns a score -3 to +3 with brief reasons

Caches results for 30 minutes to avoid hammering APIs.
Falls back to 0.0 (neutral) if either API is unavailable.
"""

import json
import logging
from datetime import datetime, timedelta, timezone

import httpx
from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)

_FINNHUB_BASE = "https://finnhub.io/api/v1"
_CACHE_TTL = 30 * 60  # 30 minutes


class SentimentAnalyzer:
    def __init__(self, finnhub_api_key: str, anthropic_api_key: str):
        self._finnhub_key = finnhub_api_key
        self._cache: dict[str, tuple[float, dict]] = {}
        self._client = httpx.AsyncClient(timeout=15.0)
        self._anthropic = AsyncAnthropic(api_key=anthropic_api_key)

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

        headlines = await self._fetch_news(symbol)
        if not headlines:
            result = {"score": 0.0, "reasons": ["No recent news found"], "source": "none"}
            self._store(symbol, result)
            return result

        result = await self._score_with_claude(symbol, headlines)
        self._store(symbol, result)
        return result

    async def _fetch_news(self, symbol: str) -> list[str]:
        """Fetch up to 10 recent news headlines from Finnhub."""
        # Strip .TO suffix for Finnhub (it uses plain TSX symbols without suffix)
        finnhub_symbol = symbol.replace(".TO", "") if symbol.endswith(".TO") else symbol

        to_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        from_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")

        url = (
            f"{_FINNHUB_BASE}/company-news"
            f"?symbol={finnhub_symbol}&from={from_date}&to={to_date}&token={self._finnhub_key}"
        )
        try:
            resp = await self._client.get(url)
            resp.raise_for_status()
            articles = resp.json()
        except Exception as e:
            logger.warning(f"SentimentAnalyzer: Finnhub news fetch failed for {symbol}: {e}")
            return []

        if not isinstance(articles, list) or not articles:
            return []

        # Extract headlines, deduplicate, limit to 10
        headlines = []
        seen = set()
        for article in articles[:20]:
            headline = article.get("headline", "").strip()
            if headline and headline not in seen:
                seen.add(headline)
                headlines.append(headline)
                if len(headlines) >= 10:
                    break

        return headlines

    async def _score_with_claude(self, symbol: str, headlines: list[str]) -> dict:
        """Send headlines to Claude Haiku for fast sentiment scoring."""
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

            # Parse JSON response
            parsed = json.loads(content)
            score = float(parsed.get("score", 0.0))
            score = max(-3.0, min(3.0, score))  # clamp
            reasons = parsed.get("reasons", [])
            if not isinstance(reasons, list):
                reasons = [str(reasons)]

            return {"score": round(score, 2), "reasons": reasons, "source": "finnhub+claude"}

        except json.JSONDecodeError as e:
            logger.warning(f"SentimentAnalyzer: Claude returned non-JSON for {symbol}: {e}")
            return {"score": 0.0, "reasons": ["Sentiment parsing failed"], "source": "error"}
        except Exception as e:
            logger.warning(f"SentimentAnalyzer: Claude API error for {symbol}: {e}")
            return {"score": 0.0, "reasons": ["Sentiment API unavailable"], "source": "error"}
