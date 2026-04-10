# Signal Quality & Profitability Roadmap

> Research-backed improvements ranked by profit impact.
> Based on academic finance literature, quant research, and structural analysis of the current codebase.

---

## Status

**Phase A complete (3/3 quick wins):** 200-day SMA filter, optimizer learning rate, sentiment asymmetry
**Phase B complete (3/3 core improvements):** Position sizing, decorrelated scoring, trend template
**Phase C pending (4 advanced):** Phased trailing stop, 52w high proximity, regime sizing, HMM

135 backend tests + 30 frontend tests passing.

---

## Current System Performance

| Metric | Current | Target |
|---|---|---|
| Win Rate | ~35% | 50-60% |
| Avg Win:Loss | ~1.0x | 1.5-2.0x |
| Profit Factor | ~0.8 | 1.5-2.5 |
| Annual Return | Negative (early) | 12-25% |

---

## Priority 1 — High Impact, Low Complexity

### 1.1 Position Size Calculator

**Status:** ✅ DONE (commit 3e6349d)
**Impact:** Highest single improvement
**Evidence:** Van Tharp, Turtle Traders, Monte Carlo simulations

**Problem:** System says BUY/SELL but never says how much. A $5 micro-cap gets same treatment as $200 blue chip.

**Solution:** Fixed fractional risk model:
```
risk_per_trade = portfolio_equity * 0.01   # 1% risk
position_size = risk_per_trade / (entry_price - stop_loss)
```

**Enhancements:**
- ATR-based sizing: `position_size = account_risk / (ATR * multiplier)` — equalizes risk across volatile and calm stocks
- Conviction overlay: scale base position ±25% based on signal conviction (AQR research shows modest Sharpe improvement)
- Kelly fraction: half-Kelly for aggressive, quarter-Kelly for conservative

**Files to modify:** `backend/app/engine/analyzer.py` (add `suggested_position_size` to signal output), `backend/app/positions/manager.py`, frontend TradeEntryForm

---

### 1.2 Trend Template Pre-Filter (Minervini Style)

**Status:** ✅ DONE (commit 83a9b07)
**Impact:** High — eliminates the largest class of losing trades
**Evidence:** Mark Minervini (334% return, 2021 USIC championship), O'Neil research (95% of 10-baggers passed this template before their move)

**Problem:** Screener scores all ~4,700 stocks. Many are in structural downtrends that should never be BUY candidates.

**Solution:** Hard pre-filter — stocks failing ANY criterion don't enter scoring:
```
1. Price > 150-day SMA (both rising)
2. Price > 200-day SMA (both rising)
3. Price within 25% of 52-week high
4. Price 30%+ above 52-week low
5. Relative Strength ranking > 70th percentile
```

**Implementation:** ~30 lines in `screener.py`, requires 252 daily bars (already fetching 60, need to increase).

**Files to modify:** `backend/app/discovery/screener.py` (add `_passes_trend_template()` pre-filter), `backend/app/engine/massive_provider.py` (increase daily bar lookback to 252)

---

### 1.3 200-Day SMA Hard Filter for BUY Signals

**Status:** ✅ DONE (commit 9118193)
**Impact:** Medium-High — strongest documented trend filter
**Evidence:** Every major swing trading methodology (Minervini, O'Neil, Weinstein)

**Problem:** Current weekly filter applies a -1.5 penalty for downtrends, but a strong RSI oversold signal (+2.0) can still overcome it. Result: BUY signals on falling knives.

**Solution:** In `analyzer.py`, hard-block BUY signals when price < 200-day SMA:
```python
if signal_type == "BUY" and current_price < sma_200:
    signal_type = "HOLD"
    tech_reasons.append("Below 200-day SMA — no BUY in downtrend")
```

**Exception:** Allow if regime is explicitly `mean_reverting` AND ADX < 20 (range-bound market).

**Files to modify:** `backend/app/engine/analyzer.py`

---

## Priority 2 — High Impact, Medium Complexity

### 2.1 Decorrelate Indicator Scoring

**Status:** ✅ DONE (commit 7685ded)
**Impact:** High — prevents false confidence from redundant signals
**Evidence:** Statistical best practice; current system triple-counts momentum

**Problem:** RSI, Stochastic, and Bollinger %B all measure overbought/oversold. When all three agree, conviction inflates by ~4.0 for what is really one signal.

**Solution:** Group indicators into independent clusters, take best signal per cluster:

| Cluster | Indicators | Max Contribution |
|---|---|---|
| Momentum | RSI, Stochastic (pick stronger) | ±2.0 |
| Trend | EMA crossover, MACD (pick stronger) | ±2.0 |
| Volatility | Bollinger %B, ADX (independent) | ±1.5 |
| Divergence | RSI divergence (standalone) | ±1.5 |
| Volume | Volume ratio (confirmation multiplier) | 0.6x-1.3x |

**Files to modify:** `backend/app/engine/analyzer.py` (`_score_technical` method)

---

### 2.2 Phased Trailing Stop

**Status:** PARTIALLY IMPLEMENTED (single-phase trailing stop exists)
**Impact:** Medium-High — locks in profits while letting winners run
**Evidence:** LeBeau & Kestner backtests converge on 3.0x ATR optimal trailing distance

**Problem:** Current trailing stop activates at +1.5% with fixed 2.0x ATR trail. For volatile stocks, +1.5% happens intraday — stop engages too fast and gets hit on normal noise.

**Solution:** Three-phase stop system:
```
Phase 1 (entry → +1 ATR profit): Fixed stop at 2.0x ATR below entry
Phase 2 (+1 ATR → +2 ATR profit): Move stop to breakeven
Phase 3 (+2 ATR profit onward): Trail at 3.0x ATR below highest close
```

**Additional:** Consider removing fixed profit targets entirely for trend trades. Let the trailing stop determine the exit — this captures outlier winners that fixed targets miss.

**Files to modify:** `backend/app/positions/exit_strategies/trailing_stop.py`

---

### 2.3 Reduce Sentiment Weight + Asymmetric Scoring

**Status:** ✅ DONE (commit b300d6c)
**Impact:** Medium
**Evidence:** Tetlock 2007 (Journal of Finance) — negative sentiment is 2-3x more informative than positive

**Problem:** Sentiment has 30% weight. Positive news is largely noise (markets price in optimism). Treating +2.0 and -2.0 sentiment identically loses edge.

**Solution:**
1. Reduce sentiment weight: 30% → 15-20%
2. Asymmetric scoring: negative sentiment gets 2x multiplier
3. Contrarian overlay: extreme positive sentiment (>2.5) slightly reduces score
```python
if sentiment_score < 0:
    sentiment_score *= 1.5  # amplify negative
elif sentiment_score > 2.5:
    sentiment_score *= 0.7  # discount extreme positive (contrarian)
```
4. Redistribute freed weight to technicals (most reliable for swing)

**Files to modify:** `backend/app/engine/analyzer.py`, `backend/app/adaptation/layer2_regime/presets.py`

---

## Priority 3 — Medium Impact

### 3.1 52-Week High Proximity Screener Factor

**Status:** NOT IMPLEMENTED
**Impact:** Medium
**Evidence:** George & Hwang 2004 (Journal of Finance) — stocks within 5% of 52-week high outperform by ~0.45%/month risk-adjusted. Stronger predictor than traditional momentum.

**Implementation:** One metric in screener scoring:
```python
week52_proximity = current_price / max(closes[-252:])
# Score: 0.95-1.0 = 10pts, 0.85-0.95 = 7pts, 0.75-0.85 = 4pts, <0.75 = 1pt
```

**Files to modify:** `backend/app/discovery/screener.py` (add to `_score_stock`, requires 252 bars)

---

### 3.2 Optimizer Learning Rate Fix

**Status:** ✅ DONE (commit 9118193)
**Impact:** Medium — prevents parameter oscillation
**Evidence:** Online learning best practices; current 0.05 is 2.5-5x too aggressive

**Problem:** `learning_rate=0.05` with `decay=0.995`. After 50 trades, lr is still 0.025 — making 2.5% parameter swings per trade. Parameters oscillate instead of converging.

**Solution:**
1. Reduce learning rate: 0.05 → 0.015
2. Add momentum (EMA of adjustments): `adjustment = 0.7 * prev_adjustment + 0.3 * new_adjustment`
3. Add convergence tracking: if parameter hasn't moved >1% in 10 trades, stop adjusting it
4. Track risk-adjusted returns per trade, not raw PnL

**Files to modify:** `backend/app/adaptation/layer1_optimizer/optimizer.py`

---

### 3.3 Regime-Based Position Sizing

**Status:** NOT IMPLEMENTED
**Impact:** Medium
**Evidence:** Daniel & Moskowitz 2016 ("Momentum Crashes"), Guidolin & Timmermann 2007

**Problem:** Regime detection changes indicator parameters, but the biggest lever is position SIZE:
- Bull regime: full size (100%)
- Transition: reduced (70%)
- Bear/volatile: significantly reduced (40-50%)

This alone improves Sharpe by ~0.15-0.25 and reduces max drawdown by 25-40%.

**Files to modify:** `backend/app/engine/analyzer.py` (add `suggested_size_pct` to signal), regime presets

---

### 3.4 HMM Regime Detection (Replace Heuristic)

**Status:** NOT IMPLEMENTED (hmmlearn already in requirements)
**Impact:** Medium
**Evidence:** Bulla et al. 2011 — HMMs detect regime changes 1-3 weeks earlier than moving-average rules

**Problem:** Current heuristic uses hard-coded thresholds (`atr_pct > 0.03` = choppy, `norm_slope > 0.002` = trending). These are arbitrary and not validated against historical data.

**Solution:**
1. Train 3-state HMM on 5 years of SPY daily returns
2. States: bull, bear, transition
3. Use posterior probabilities instead of hard classification
4. Reduce from 5 regimes to 3 (more robust, less overfitting)

**Files to modify:** `backend/app/engine/regime.py`, `backend/app/adaptation/layer2_regime/`

---

## Priority 4 — Lower Impact / Future Work

### 4.1 RSI(2) Secondary Trigger

**Evidence:** Connors RSI(2) mean reversion — 75-85% win rate on stocks above 200-day SMA. Buy when RSI(2) < 10, sell when > 70. Well-documented 2-7 day hold strategy.

### 4.2 Z-Score Normalize Screener Factors

Cross-sectional z-score normalization within daily scan. Professional factor models always normalize — raw scores bias toward volatile stocks.

### 4.3 MACD Normalization Fix

Current: `macd_hist / current_price * 100`. For $5 stock, small moves = 2% of price. For $200 stock, same move = 0.25%. Introduces price-level bias. Fix: normalize by ATR instead of price.

### 4.4 Sentiment Decay Constant

Current: `exp(-0.15 * days)` — 7-day-old news is 65% discounted. For swing trading (days-weeks hold), news from 3 days ago is often still the primary driver. Suggested: `exp(-0.05 * days)` (7-day-old = 71% weight).

### 4.5 Source Credibility Weighting

Not all news sources are equal. Bloomberg moves prices; Reddit doesn't. Weight Massive news articles by publisher credibility.

### 4.6 Earnings Date Catalyst Detection

Current news score treats "earnings surprise" same as "CEO interview." Flag upcoming/recent earnings dates as high-volatility catalysts with asymmetric scoring.

---

## Realistic Benchmarks

| Strategy Type | Win Rate | Avg Win:Loss | Profit Factor | Max Drawdown | Annual Return |
|---|---|---|---|---|---|
| Trend-following swing | 35-45% | 2.0-3.0x | 1.3-2.0 | 15-25% | 10-25% |
| Mean-reversion swing | 60-75% | 0.7-1.2x | 1.3-1.8 | 10-15% | 8-18% |
| Hybrid (pullback in trend) | 50-60% | 1.5-2.0x | 1.5-2.5 | 12-20% | 12-25% |
| Minervini/O'Neil style | 40-50% | 2.5-4.0x | 1.8-3.0 | 10-20% | 15-40% |

**Minimum viable thresholds:** Profit Factor > 1.5, Expectancy > 0.5R per trade, Sharpe > 0.8

---

## Implementation Order

```
Phase A (Quick Wins — 1-2 days) — ✅ DONE:
  ✅ 1.3  200-day SMA hard filter           (commit 9118193)
  ✅ 3.2  Optimizer learning rate fix       (commit 9118193)
  ✅ 2.3  Sentiment asymmetric scoring      (commit b300d6c)

Phase B (Core Improvements — 3-5 days) — ✅ DONE:
  ✅ 1.1  Position size calculator          (commit 3e6349d)
  ✅ 2.1  Decorrelate indicator scoring     (commit 7685ded)
  ✅ 1.2  Trend template pre-filter         (commit 83a9b07)

Phase C (Advanced — 1-2 weeks) — pending:
  ⏳ 2.2  Phased trailing stop
  ⏳ 3.1  52-week high proximity
  ⏳ 3.3  Regime-based position sizing
  ⏳ 3.4  HMM regime detection
```

---

**Disclaimer:** Educational/informational only. Not financial advice. Backtested results do not guarantee future performance. All cited research is from published academic literature and documented practitioner results.
