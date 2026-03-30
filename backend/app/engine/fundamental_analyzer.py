"""
Real fundamental analysis using Finnhub basic financials + analyst recommendations.

Flow:
  1. Fetch basic financials from Finnhub /stock/metric (P/E, P/B, ROE, etc.)
  2. Fetch analyst recommendations from Finnhub /stock/recommendation
  3. Score each metric and produce a composite fundamental score (-2 to +2)

Caches results for 6 hours (fundamentals don't change intraday).
Falls back to 0.0 (neutral) if API is unavailable.
"""

import logging
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

_FINNHUB_BASE = "https://finnhub.io/api/v1"
_CACHE_TTL = 6 * 60 * 60  # 6 hours


class FundamentalAnalyzer:
    def __init__(self, finnhub_api_key: str):
        self._key = finnhub_api_key
        self._cache: dict[str, tuple[float, dict]] = {}
        self._client = httpx.AsyncClient(timeout=15.0)

    def _cached(self, symbol: str) -> dict | None:
        if symbol in self._cache:
            fetched_at, data = self._cache[symbol]
            if datetime.now(timezone.utc).timestamp() - fetched_at < _CACHE_TTL:
                return data
        return None

    def _store(self, symbol: str, data: dict) -> None:
        self._cache[symbol] = (datetime.now(timezone.utc).timestamp(), data)

    async def get_fundamentals(self, symbol: str) -> dict:
        """
        Returns:
            {score: float (-2 to +2), reasons: list[str], metrics: dict, source: str}
        """
        cached = self._cached(symbol)
        if cached is not None:
            return cached

        # Strip .TO for Finnhub
        finnhub_symbol = symbol.replace(".TO", "") if symbol.endswith(".TO") else symbol

        metrics = await self._fetch_metrics(finnhub_symbol)
        recommendations = await self._fetch_recommendations(finnhub_symbol)

        if not metrics and not recommendations:
            result = {
                "score": 0.0,
                "reasons": ["No fundamental data available"],
                "metrics": {},
                "source": "none",
            }
            self._store(symbol, result)
            return result

        score, reasons, cleaned_metrics = self._score(metrics, recommendations)
        result = {
            "score": round(score, 2),
            "reasons": reasons,
            "metrics": cleaned_metrics,
            "source": "finnhub",
        }
        self._store(symbol, result)
        return result

    async def _fetch_metrics(self, symbol: str) -> dict:
        """Fetch basic financials from Finnhub /stock/metric."""
        url = f"{_FINNHUB_BASE}/stock/metric?symbol={symbol}&metric=all&token={self._key}"
        try:
            resp = await self._client.get(url)
            resp.raise_for_status()
            data = resp.json()
            return data.get("metric", {})
        except Exception as e:
            logger.warning("FundamentalAnalyzer: metrics fetch failed for %s: %s", symbol, e)
            return {}

    async def _fetch_recommendations(self, symbol: str) -> dict | None:
        """Fetch latest analyst recommendation from Finnhub /stock/recommendation."""
        url = f"{_FINNHUB_BASE}/stock/recommendation?symbol={symbol}&token={self._key}"
        try:
            resp = await self._client.get(url)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and data:
                return data[0]  # Most recent
            return None
        except Exception as e:
            logger.warning("FundamentalAnalyzer: recommendations fetch failed for %s: %s", symbol, e)
            return None

    def _score(
        self, metrics: dict, recommendations: dict | None
    ) -> tuple[float, list[str], dict]:
        """Score fundamentals on a -2 to +2 scale."""
        sub_scores: list[float] = []
        reasons: list[str] = []
        cleaned: dict = {}

        # --- P/E ratio ---
        pe = metrics.get("peNormalizedAnnual") or metrics.get("peBasicExclExtraTTM")
        if pe is not None and pe > 0:
            cleaned["pe_ratio"] = round(pe, 1)
            if pe < 15:
                sub_scores.append(2.0)
                reasons.append(f"Low P/E ({pe:.1f}) — attractively valued")
            elif pe < 25:
                sub_scores.append(0.5)
                reasons.append(f"Moderate P/E ({pe:.1f})")
            elif pe < 40:
                sub_scores.append(-0.5)
                reasons.append(f"High P/E ({pe:.1f}) — premium valuation")
            else:
                sub_scores.append(-1.5)
                reasons.append(f"Very high P/E ({pe:.1f}) — expensive")

        # --- P/B ratio ---
        pb = metrics.get("pbAnnual") or metrics.get("pbQuarterly")
        if pb is not None and pb > 0:
            cleaned["pb_ratio"] = round(pb, 1)
            if pb < 1.5:
                sub_scores.append(1.5)
                reasons.append(f"Low P/B ({pb:.1f}) — potential value play")
            elif pb < 3.0:
                sub_scores.append(0.5)
            elif pb < 8.0:
                sub_scores.append(-0.5)
            else:
                sub_scores.append(-1.0)
                reasons.append(f"High P/B ({pb:.1f})")

        # --- ROE ---
        roe = metrics.get("roeTTM") or metrics.get("roeRfy")
        if roe is not None:
            cleaned["roe"] = round(roe, 1)
            if roe > 20:
                sub_scores.append(2.0)
                reasons.append(f"Strong ROE ({roe:.1f}%) — efficient capital use")
            elif roe > 10:
                sub_scores.append(1.0)
                reasons.append(f"Solid ROE ({roe:.1f}%)")
            elif roe > 0:
                sub_scores.append(0.0)
            else:
                sub_scores.append(-1.5)
                reasons.append(f"Negative ROE ({roe:.1f}%) — unprofitable")

        # --- Profit margin ---
        margin = metrics.get("netProfitMarginTTM") or metrics.get("netProfitMarginAnnual")
        if margin is not None:
            cleaned["profit_margin"] = round(margin, 1)
            if margin > 20:
                sub_scores.append(1.5)
                reasons.append(f"High profit margin ({margin:.1f}%)")
            elif margin > 10:
                sub_scores.append(0.5)
            elif margin > 0:
                sub_scores.append(0.0)
            else:
                sub_scores.append(-1.0)
                reasons.append(f"Negative margin ({margin:.1f}%)")

        # --- Debt/Equity ---
        de = metrics.get("totalDebt/totalEquityAnnual") or metrics.get("totalDebt/totalEquityQuarterly")
        if de is not None and de >= 0:
            cleaned["debt_to_equity"] = round(de, 2)
            if de < 0.5:
                sub_scores.append(1.5)
                reasons.append(f"Low debt/equity ({de:.2f}) — strong balance sheet")
            elif de < 1.0:
                sub_scores.append(0.5)
            elif de < 2.0:
                sub_scores.append(-0.5)
            else:
                sub_scores.append(-1.5)
                reasons.append(f"High debt/equity ({de:.2f}) — leveraged")

        # --- Revenue growth ---
        rev_growth = metrics.get("revenueGrowthQuarterlyYoy") or metrics.get("revenueGrowth3Y")
        if rev_growth is not None:
            cleaned["revenue_growth"] = round(rev_growth, 1)
            if rev_growth > 20:
                sub_scores.append(2.0)
                reasons.append(f"Strong revenue growth ({rev_growth:.1f}%)")
            elif rev_growth > 5:
                sub_scores.append(0.5)
            elif rev_growth > 0:
                sub_scores.append(0.0)
            else:
                sub_scores.append(-1.0)
                reasons.append(f"Revenue declining ({rev_growth:.1f}%)")

        # --- Analyst recommendations ---
        if recommendations:
            buy = recommendations.get("buy", 0) + recommendations.get("strongBuy", 0)
            sell = recommendations.get("sell", 0) + recommendations.get("strongSell", 0)
            hold = recommendations.get("hold", 0)
            total = buy + sell + hold
            cleaned["analyst_buy"] = buy
            cleaned["analyst_hold"] = hold
            cleaned["analyst_sell"] = sell
            if total > 0:
                buy_pct = buy / total
                sell_pct = sell / total
                if buy_pct > 0.6:
                    sub_scores.append(1.5)
                    reasons.append(f"Analyst consensus: strong buy ({buy}/{total} buy)")
                elif buy_pct > 0.4:
                    sub_scores.append(0.5)
                    reasons.append(f"Analyst consensus: moderate buy ({buy}/{total} buy)")
                elif sell_pct > 0.4:
                    sub_scores.append(-1.5)
                    reasons.append(f"Analyst consensus: sell ({sell}/{total} sell)")
                else:
                    sub_scores.append(0.0)
                    reasons.append(f"Analyst consensus: hold ({hold}/{total} hold)")

        if not sub_scores:
            return 0.0, ["Insufficient fundamental data"], cleaned

        score = sum(sub_scores) / len(sub_scores)
        score = max(-2.0, min(2.0, score))

        if not reasons:
            if score > 0.5:
                reasons.append("Generally favorable fundamentals")
            elif score < -0.5:
                reasons.append("Generally weak fundamentals")
            else:
                reasons.append("Mixed fundamentals")

        return score, reasons, cleaned
