# Plan: Replace Finnhub with Massive API + Expand Watchlist

## Context

Finnhub's free tier (60 calls/min) is the bottleneck limiting watchlist size and causing 429 errors. Massive.com (Stocks Starter, $29/month) has **unlimited API calls** and provides:

1. **Ticker News with built-in sentiment** — `GET /v2/reference/news?ticker=AAPL` returns articles with an `insights` array containing per-ticker `sentiment` and `sentiment_reasoning`. This could replace both Finnhub news AND Claude Haiku sentiment scoring.

2. **OHLCV data** — already using this via `/v2/aggs` (working).

3. **Financials** — needs verification, but Polygon-style APIs typically offer `/vX/reference/financials` for quarterly/annual data.

**Goals:**
- Replace all Finnhub calls with Massive (unlimited, no rate limits)
- Expand watchlist from 12 to 20 picks
- Use Massive's built-in sentiment instead of Claude Haiku (saves ~$0.01/refresh)
- Remove all Finnhub rate-limiting delays from screener

---

## Phase 1: Replace Sentiment Analyzer (Finnhub news + Claude → Massive news + built-in sentiment)

### 1.1 Create MassiveSentimentAnalyzer

**New file:** `backend/app/engine/massive_sentiment.py`

Replaces the current flow (Finnhub news → Claude Haiku scoring) with:
```
GET https://api.massive.com/v2/reference/news
  ?ticker={symbol}
  &published_utc.gte={7_days_ago}
  &limit=10
  &sort=published_utc
  &order=desc
  &apiKey={massive_key}
```

Response includes per-article `insights`:
```json
{
  "insights": [
    {
      "ticker": "AAPL",
      "sentiment": "positive",   // or "negative", "neutral"
      "sentiment_reasoning": "Strong earnings beat..."
    }
  ]
}
```

**Scoring logic:**
- Map each article's sentiment: positive = +1, neutral = 0, negative = -1
- Weight by recency (exponential decay: 1-day-old = 1.0, 7-day-old = 0.3)
- Average weighted scores, scale to -3 to +3 range
- Extract `sentiment_reasoning` strings as reasons
- Cache for 30 minutes (same as current)
- Fallback: if no `insights` in response, extract headlines and use Claude Haiku (keep as backup)

### 1.2 Update analyzer.py singleton

**File:** `backend/app/engine/analyzer.py`
- Change `_get_sentiment()` to create `MassiveSentimentAnalyzer` when `massive_api_key` is set
- Fall back to current `SentimentAnalyzer` (Finnhub+Claude) if only `finnhub_api_key` is set
- Fall back to simulated if neither

### 1.3 Update screener news score

**File:** `backend/app/discovery/screener.py` — `_fetch_news_score()` method
- Replace Finnhub `/company-news` call with Massive `/v2/reference/news`
- Same logic: count articles in last 3 days, map to 0-10 score
- Remove `BATCH_DELAY_SECS` rate limiting (Massive is unlimited)

**Files modified:** `screener.py` lines 78-82 (batch config), lines 316-345 (`_fetch_news_score`)

---

## Phase 2: Replace Fundamental Analyzer (Finnhub metrics → Massive financials)

### 2.1 Test Massive financials endpoint

Need to verify if the Stocks Starter plan includes:
```
GET https://api.massive.com/vX/reference/financials?ticker=AAPL&limit=1&apiKey={key}
```

If available: replace Finnhub `/stock/metric` with Massive financials data.
If not available: keep Finnhub for fundamentals only (low call volume — only 12-20 calls per 30 min, well within limits).

### 2.2 Update FundamentalAnalyzer (if Massive financials available)

**File:** `backend/app/engine/fundamental_analyzer.py`
- Replace `_fetch_metrics()` to use Massive financials endpoint
- Replace `_fetch_recommendations()` — may not have direct equivalent; if not, keep Finnhub for this one call or drop analyst consensus
- Update field name mapping (Polygon uses different field names than Finnhub)

### 2.3 Fallback strategy

If Massive doesn't cover all fundamental metrics:
- **Option A**: Hybrid — Massive for news/sentiment, Finnhub for fundamentals only (few calls, within limit)
- **Option B**: Compute ratios from raw financial statements (Massive provides revenue, net income, etc.)

---

## Phase 3: Expand Watchlist + Remove Rate Limits

### 3.1 Increase watchlist size

**File:** `backend/app/config.py` — `watchlist_size: int = 12` → `20`
**File:** `.env` and `.env.example` — `WATCHLIST_SIZE=20`

### 3.2 Remove screener rate limiting

**File:** `backend/app/discovery/screener.py`
- `BATCH_SIZE = 30` → `50` (Massive is unlimited)
- `BATCH_DELAY_SECS = 35.0` → `2.0` (just a brief pause to avoid network saturation)
- Scan time drops from ~92 min to ~10 min

### 3.3 Update AI watchlist prompt

**File:** `backend/app/discovery/ai_watchlist.py`
- Already updated for swing trading (from previous work)
- Change `size` parameter from 12 to 20 in the prompt

---

## Phase 4: Route by Exchange — Massive (US) vs Finnhub (.TO)

Massive only covers US stocks. Canadian .TO stocks keep using Finnhub (low volume — ~100 TSX symbols, well within 60/min).

### 4.1 Hybrid routing in analyzer

**File:** `backend/app/engine/analyzer.py`
- `analyze()` checks if symbol ends with `.TO`
- US → `MassiveSentimentAnalyzer` + Massive fundamentals (unlimited)
- `.TO` → existing `SentimentAnalyzer` (Finnhub+Claude) + existing `FundamentalAnalyzer` (Finnhub)

### 4.2 Hybrid routing in screener

**File:** `backend/app/discovery/screener.py` — `_fetch_news_score()`
- US → Massive `/v2/reference/news` (no rate limit)
- `.TO` → Finnhub `/company-news` (keep existing, low volume)

### 4.3 Keep Finnhub config

- `finnhub_api_key` stays in config (used for .TO only)
- `sentiment_analyzer.py` and `fundamental_analyzer.py` kept (used for .TO)

---

## Files Modified

| File | Change |
|------|--------|
| `backend/app/engine/massive_sentiment.py` (NEW) | Massive news API with built-in sentiment for US stocks |
| `backend/app/engine/analyzer.py` | Route US → Massive, .TO → Finnhub |
| `backend/app/discovery/screener.py` | Route US → Massive news, .TO → Finnhub news; remove rate limits for US |
| `backend/app/engine/fundamental_analyzer.py` | Keep for .TO; add Massive fundamentals for US (if available) |
| `backend/app/engine/sentiment_analyzer.py` | Keep for .TO fallback |
| `backend/app/config.py` | `watchlist_size` 12 → 20, keep `finnhub_api_key` |
| `.env` / `.env.example` | `WATCHLIST_SIZE=20` |

---

## Verification

1. **Sentiment**: Run `.\run.ps1 watchlist` — check logs for Massive news API calls instead of Finnhub. Verify sentiment scores are populated on signals.

2. **No 429 errors**: Run `.\run.ps1 scan` — should complete without any rate limit errors. Check scan time drops from ~90 min to ~10 min.

3. **Watchlist size**: After scan + watchlist build, verify 20 picks: `SELECT count(*) FROM daily_watchlist WHERE watch_date = CURRENT_DATE;`

4. **Signals**: Refresh the Signals tab — should show 20 stocks with sentiment scores derived from Massive insights.

5. **Fundamentals**: If switched to Massive, verify P/E, ROE, etc. still populate on the Fundamental tab. If kept on Finnhub, verify no 429s (only 20 calls per 6-hour cache cycle).

---

## Risk

- **Massive `insights` may not be on Stocks Starter** — we test the endpoint first. If no built-in sentiment, use Massive for headlines + Claude Haiku for scoring (same quality, just different news source).
- **Massive financials may not exist on Starter** — keep Finnhub for all fundamentals (US + .TO). Low call volume (20 per 6-hour cache) is fine.
- **.TO stocks** — Finnhub stays for Canadian stocks only. Very low call volume (~100 TSX symbols), no rate limit concern.
