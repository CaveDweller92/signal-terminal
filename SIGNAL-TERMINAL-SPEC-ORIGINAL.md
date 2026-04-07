# Signal Terminal — Adaptive Intraday Trading System

## Project Overview

A self-adapting intraday stock trading signals platform that:

1. **Discovers stocks** — Pre-market screener scans S&P 500, NASDAQ 100, and TSX/TSX Venture, then Claude curates a personalized daily watchlist
2. **Generates entry signals** — Combines technical analysis, news sentiment, and fundamental health into a conviction score → BUY / SELL / HOLD
3. **Manages active positions** — Tracks your open trades and generates real-time EXIT signals via profit targets, stop losses, indicator reversals, sentiment shifts, and time-based EOD alerts
4. **Adapts itself** — 3-layer adaptive intelligence optimizes both entry AND exit parameters, detects regime shifts, and reviews strategy health daily

The system runs autonomously — every morning you get a fresh watchlist, entry signals throughout the day, and active exit monitoring on every position you open.

> **Disclaimer:** Educational/informational purposes only. Not financial advice. No system guarantees profits. Trade only what you can afford to lose.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          DAILY PIPELINE                                 │
│  5:00 AM  Pre-market Screener (830 stocks)                             │
│  6:00 AM  Claude Watchlist Build (12 picks)                            │
│  9:30 AM  Signal Engine + Position Monitor Active                      │
│  Ongoing  EXIT alerts on open positions (stop/target/reversal/sentiment)│
│  3:45 PM  EOD exit warnings on all open positions                      │
│  4:15 PM  Daily Meta-Review (Claude)                                   │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────────┐
│                     FRONTEND (React + TypeScript)                       │
│  Dashboard · Charts · Dynamic Watchlist · Position Tracker              │
│  Exit Alerts · Screener · AI Picks · Adaptation · Performance           │
└────────────────────────────┬────────────────────────────────────────────┘
                             │  REST + WebSocket
┌────────────────────────────▼────────────────────────────────────────────┐
│                      API GATEWAY (FastAPI)                              │
│  /api/signals · /api/positions · /api/screener · /api/watchlist         │
│  /api/regime · /api/adaptation · /api/performance · /ws/live            │
└──┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────────┘
   │          │          │          │          │          │
┌──▼───┐ ┌───▼────┐ ┌───▼────┐ ┌───▼────┐ ┌───▼────┐ ┌──▼──────────────┐
│Pos.  │ │Screen- │ │Layer 1 │ │Layer 2 │ │Layer 3 │ │Data Services   │
│Mgr + │ │er + AI │ │Online  │ │Regime  │ │Claude  │ │Market Data API │
│Exit  │ │Watch-  │ │Optim.  │ │Detect. │ │Meta-   │ │News API        │
│Engine│ │list    │ │Bayesian│ │HMM/XGB │ │Analyst │ │Fundamentals    │
└──────┘ └────────┘ └────────┘ └────────┘ └────────┘ └────────────────┘
                             │
                    ┌────────▼────────┐
                    │  PostgreSQL +   │
                    │  Redis Cache    │
                    └─────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18+, TypeScript, Vite, Recharts, Tailwind CSS |
| Backend | Python 3.11+, FastAPI, Uvicorn |
| ML/Stats | scikit-learn, scipy, numpy, pandas, hmmlearn |
| AI Agent | Anthropic Claude API (claude-sonnet-4-20250514) |
| Database | PostgreSQL 16 + SQLAlchemy / Alembic |
| Cache | Redis (market data + screener results TTL cache) |
| Task Queue | Celery + Redis |
| WebSocket | FastAPI WebSocket for live signals + exit alerts |
| Notifications | Resend (email), Web Push API (browser) |
| Market Data | Massive.com (US) + yfinance (TSX) + Finnhub news (simulated in Phase 1) |
| DevOps | Docker Compose, GitHub Actions CI |

---

## Project Structure

```
signal-terminal/
│
├── frontend/
│   ├── public/
│   │   └── favicon.svg
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── index.css
│   │   │
│   │   ├── config/
│   │   │   ├── defaults.ts              # Default strategy + exit params
│   │   │   ├── api.ts                   # API endpoints
│   │   │   └── universes.ts             # Universe labels
│   │   │
│   │   ├── types/
│   │   │   ├── market.ts               # PriceBar, StockAnalysis, Signal
│   │   │   ├── sentiment.ts            # Headline, SentimentScore
│   │   │   ├── fundamentals.ts         # FundamentalData, RadarPoint
│   │   │   ├── adaptation.ts           # RegimeState, OptimizationLog, MetaReview
│   │   │   ├── screener.ts             # ScreenerResult, WatchlistPick
│   │   │   ├── positions.ts            # Position, ExitSignal, ExitRule, TradeLog
│   │   │   └── api.ts                  # API request/response types
│   │   │
│   │   ├── services/
│   │   │   ├── api.ts
│   │   │   ├── websocket.ts
│   │   │   └── notifications.ts
│   │   │
│   │   ├── hooks/
│   │   │   ├── useAnalyses.ts
│   │   │   ├── useAlerts.ts
│   │   │   ├── useRegime.ts
│   │   │   ├── useAdaptation.ts
│   │   │   ├── usePerformance.ts
│   │   │   ├── useWatchlist.ts
│   │   │   ├── useScreener.ts
│   │   │   ├── usePositions.ts          # Active positions + exit alerts
│   │   │   ├── useTradeLog.ts           # Closed trade history
│   │   │   └── useLiveUpdates.ts
│   │   │
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── Header.tsx
│   │   │   │   ├── Watchlist.tsx
│   │   │   │   └── DetailPanel.tsx
│   │   │   │
│   │   │   ├── common/
│   │   │   │   ├── SignalBadge.tsx
│   │   │   │   ├── StatBox.tsx
│   │   │   │   ├── MiniChart.tsx
│   │   │   │   ├── Tabs.tsx
│   │   │   │   ├── RegimeBadge.tsx
│   │   │   │   ├── ExchangeBadge.tsx
│   │   │   │   └── ExitTypeBadge.tsx    # Stop / Target / Reversal / etc.
│   │   │   │
│   │   │   ├── charts/
│   │   │   │   ├── PriceChart.tsx       # Now shows entry/exit markers
│   │   │   │   ├── RSIChart.tsx
│   │   │   │   ├── MACDChart.tsx
│   │   │   │   ├── VolumeChart.tsx
│   │   │   │   ├── SentimentTrendChart.tsx
│   │   │   │   ├── FundamentalRadar.tsx
│   │   │   │   ├── EarningsChart.tsx
│   │   │   │   ├── ConvictionBreakdown.tsx
│   │   │   │   ├── ParameterDriftChart.tsx
│   │   │   │   ├── RegimeTimeline.tsx
│   │   │   │   ├── PerformanceChart.tsx
│   │   │   │   ├── ScreenerHeatmap.tsx
│   │   │   │   ├── PnLChart.tsx         # Per-position P&L over time
│   │   │   │   └── ExitLevelChart.tsx   # Shows stop/target levels on price
│   │   │   │
│   │   │   ├── panels/
│   │   │   │   ├── NewsFeed.tsx
│   │   │   │   ├── FundamentalsPanel.tsx
│   │   │   │   ├── AlertLog.tsx
│   │   │   │   ├── ConfigPanel.tsx
│   │   │   │   ├── AdaptationLog.tsx
│   │   │   │   ├── MetaReviewPanel.tsx
│   │   │   │   ├── ScreenerPanel.tsx
│   │   │   │   ├── WatchlistBuilder.tsx
│   │   │   │   ├── PositionPanel.tsx        # Active position details
│   │   │   │   ├── ExitAlertPanel.tsx       # Live exit signal feed
│   │   │   │   ├── TradeEntryForm.tsx       # Manual trade entry form
│   │   │   │   └── TradeHistoryPanel.tsx    # Closed trades log
│   │   │   │
│   │   │   └── tabs/
│   │   │       ├── TechnicalTab.tsx
│   │   │       ├── SentimentTab.tsx
│   │   │       ├── FundamentalsTab.tsx
│   │   │       ├── SignalsTab.tsx
│   │   │       ├── AdaptationTab.tsx
│   │   │       ├── DiscoveryTab.tsx
│   │   │       └── PositionsTab.tsx         # Active positions + trade log
│   │   │
│   │   └── styles/
│   │       └── theme.ts
│   │
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── vite.config.ts
│   └── index.html
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── signal.py
│   │   │   ├── parameter_snapshot.py
│   │   │   ├── regime_log.py
│   │   │   ├── meta_review.py
│   │   │   ├── performance.py
│   │   │   ├── screener_result.py
│   │   │   ├── watchlist.py
│   │   │   ├── stock_universe.py
│   │   │   ├── position.py              # Active + closed positions
│   │   │   └── exit_signal.py           # Exit signal history
│   │   │
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── signals.py
│   │   │   ├── config.py
│   │   │   ├── regime.py
│   │   │   ├── adaptation.py
│   │   │   ├── performance.py
│   │   │   ├── screener.py
│   │   │   ├── watchlist.py
│   │   │   └── positions.py             # Position + exit schemas
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── router.py
│   │   │   ├── signals.py
│   │   │   ├── config.py
│   │   │   ├── regime.py
│   │   │   ├── adaptation.py
│   │   │   ├── performance.py
│   │   │   ├── screener.py
│   │   │   ├── watchlist.py
│   │   │   ├── positions.py             # CRUD for positions + close trade
│   │   │   └── websocket.py             # Now pushes exit alerts too
│   │   │
│   │   ├── engine/
│   │   │   ├── __init__.py
│   │   │   ├── indicators.py
│   │   │   ├── sentiment.py
│   │   │   ├── fundamentals.py
│   │   │   ├── analyzer.py
│   │   │   └── data_provider.py
│   │   │
│   │   ├── positions/                   # POSITION MANAGEMENT SYSTEM
│   │   │   ├── __init__.py
│   │   │   ├── manager.py              # Position lifecycle orchestrator
│   │   │   ├── monitor.py              # Real-time position monitor loop
│   │   │   │
│   │   │   ├── exit_strategies/         # Exit signal generators
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py             # Abstract ExitStrategy interface
│   │   │   │   ├── profit_target.py    # Fixed + ATR-based profit targets
│   │   │   │   ├── stop_loss.py        # Fixed + ATR-based stop losses
│   │   │   │   ├── indicator_reversal.py # RSI/EMA/MACD reversal exits
│   │   │   │   ├── sentiment_shift.py  # Breaking news exit alerts
│   │   │   │   ├── time_based.py       # EOD exit + max hold time
│   │   │   │   └── composite.py        # Combines all strategies, ranks urgency
│   │   │   │
│   │   │   ├── risk.py                  # Position sizing + portfolio risk
│   │   │   ├── pnl.py                   # Real-time P&L calculator
│   │   │   └── defaults.py             # Default exit parameter configs
│   │   │
│   │   ├── discovery/
│   │   │   ├── __init__.py
│   │   │   ├── universe/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── manager.py
│   │   │   │   ├── sp500.py
│   │   │   │   ├── nasdaq100.py
│   │   │   │   ├── tsx.py
│   │   │   │   └── cache.py
│   │   │   │
│   │   │   ├── screener/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── scanner.py
│   │   │   │   ├── filters.py
│   │   │   │   ├── premarket.py
│   │   │   │   ├── technical_screen.py
│   │   │   │   ├── fundamental_screen.py
│   │   │   │   ├── news_screen.py
│   │   │   │   ├── sector_momentum.py
│   │   │   │   └── scoring.py
│   │   │   │
│   │   │   └── ai_watchlist/
│   │   │       ├── __init__.py
│   │   │       ├── builder.py
│   │   │       ├── prompts.py
│   │   │       ├── context.py
│   │   │       ├── parser.py
│   │   │       └── personalizer.py
│   │   │
│   │   ├── adaptation/
│   │   │   ├── __init__.py
│   │   │   │
│   │   │   ├── layer1_optimizer/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── optimizer.py
│   │   │   │   ├── bayesian.py
│   │   │   │   ├── bandit.py
│   │   │   │   ├── parameter_space.py   # Now includes exit params
│   │   │   │   ├── outcome_tracker.py
│   │   │   │   └── safety.py
│   │   │   │
│   │   │   ├── layer2_regime/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── detector.py
│   │   │   │   ├── features.py
│   │   │   │   ├── hmm_model.py
│   │   │   │   ├── xgb_model.py
│   │   │   │   ├── presets.py           # Now includes exit presets per regime
│   │   │   │   └── regime_types.py
│   │   │   │
│   │   │   ├── layer3_meta/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── analyst.py
│   │   │   │   ├── prompts.py           # Now reviews exit performance too
│   │   │   │   ├── summarizer.py
│   │   │   │   ├── parser.py
│   │   │   │   └── actions.py
│   │   │   │
│   │   │   └── coordinator.py
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── market_data.py
│   │   │   ├── news.py
│   │   │   ├── fundamentals_api.py
│   │   │   ├── anthropic_client.py
│   │   │   ├── notifications.py
│   │   │   └── cache.py
│   │   │
│   │   ├── tasks/
│   │   │   ├── __init__.py
│   │   │   ├── celery_app.py
│   │   │   ├── premarket_scan.py
│   │   │   ├── watchlist_build.py
│   │   │   ├── position_monitor.py      # Continuous exit monitoring task
│   │   │   ├── regime_detection.py
│   │   │   ├── daily_meta_review.py
│   │   │   ├── parameter_snapshot.py
│   │   │   ├── performance_calc.py
│   │   │   └── universe_update.py
│   │   │
│   │   └── db/
│   │       ├── __init__.py
│   │       ├── database.py
│   │       └── migrations/
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_indicators.py
│   │   ├── test_optimizer.py
│   │   ├── test_regime_detector.py
│   │   ├── test_screener.py
│   │   ├── test_watchlist_builder.py
│   │   ├── test_exit_strategies.py      # NEW
│   │   ├── test_position_manager.py     # NEW
│   │   ├── test_analyzer.py
│   │   └── test_api.py
│   │
│   ├── scripts/
│   │   ├── seed_historical.py
│   │   ├── seed_universe.py
│   │   ├── backtest.py
│   │   └── train_regime_model.py
│   │
│   ├── requirements.txt
│   ├── alembic.ini
│   └── Dockerfile
│
├── docker-compose.yml
├── .env.example
├── .gitignore
├── Makefile
└── README.md
```

---

## Setup Instructions

### Docker (Recommended)

```bash
git clone <repo-url> && cd signal-terminal
cp .env.example .env       # Edit with your API keys
docker compose up --build
```

### Manual Setup

```bash
# Backend
cd backend && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python scripts/seed_universe.py
uvicorn app.main:app --reload --port 8000

# Celery (separate terminals)
celery -A app.tasks.celery_app worker --loglevel=info
celery -A app.tasks.celery_app beat --loglevel=info

# Frontend
cd frontend && npm install && npm run dev
```

### Environment Variables

```env
DATABASE_URL=postgresql://signal:signal@localhost:5432/signal_terminal
REDIS_URL=redis://localhost:6379/0

# Market Data (blank = simulated)
MASSIVE_API_KEY=
FINNHUB_API_KEY=

# Required for Layer 3 + AI Watchlist
ANTHROPIC_API_KEY=your_key

# Optional
RESEND_API_KEY=
ALERT_EMAIL=

# App Config
TIMEZONE=America/New_York
SCREENER_UNIVERSES=sp500,nasdaq100,tsx
WATCHLIST_SIZE=12

# Exit Strategy Defaults
DEFAULT_STOP_LOSS_PCT=2.0
DEFAULT_PROFIT_TARGET_PCT=3.0
DEFAULT_ATR_MULTIPLIER_STOP=1.5
DEFAULT_ATR_MULTIPLIER_TARGET=2.5
EOD_EXIT_WARNING_MINUTES=15
MAX_HOLD_BARS=60
```

---

## Database Schema

### stock_universe

```sql
CREATE TABLE stock_universe (
    id              SERIAL PRIMARY KEY,
    symbol          VARCHAR(10) NOT NULL,
    name            VARCHAR(200) NOT NULL,
    exchange        VARCHAR(20) NOT NULL,
    universe        VARCHAR(20) NOT NULL,
    sector          VARCHAR(50),
    industry        VARCHAR(100),
    market_cap      BIGINT,
    avg_volume_30d  BIGINT,
    country         VARCHAR(5) DEFAULT 'US',
    currency        VARCHAR(3) DEFAULT 'USD',
    is_active       BOOLEAN DEFAULT true,
    last_updated    TIMESTAMP DEFAULT NOW(),
    UNIQUE(symbol, exchange)
);
```

### screener_results

```sql
CREATE TABLE screener_results (
    id                SERIAL PRIMARY KEY,
    scan_date         DATE NOT NULL,
    symbol            VARCHAR(10) NOT NULL,
    exchange          VARCHAR(20),
    composite_score   FLOAT NOT NULL,
    volume_score      FLOAT,
    gap_score         FLOAT,
    technical_score   FLOAT,
    fundamental_score FLOAT,
    news_score        FLOAT,
    sector_score      FLOAT,
    premarket_gap_pct FLOAT,
    relative_volume   FLOAT,
    sector            VARCHAR(50),
    has_catalyst      BOOLEAN DEFAULT false,
    catalyst_summary  TEXT,
    created_at        TIMESTAMP DEFAULT NOW(),
    UNIQUE(scan_date, symbol)
);
```

### daily_watchlist

```sql
CREATE TABLE daily_watchlist (
    id              SERIAL PRIMARY KEY,
    watch_date      DATE NOT NULL,
    symbol          VARCHAR(10) NOT NULL,
    exchange        VARCHAR(20),
    source          VARCHAR(20) NOT NULL,
    ai_reasoning    TEXT,
    screener_rank   INTEGER,
    sector          VARCHAR(50),
    regime_at_pick  VARCHAR(30),
    signals_generated INTEGER DEFAULT 0,
    signals_won       INTEGER DEFAULT 0,
    user_added      BOOLEAN DEFAULT false,
    user_removed    BOOLEAN DEFAULT false,
    created_at      TIMESTAMP DEFAULT NOW(),
    UNIQUE(watch_date, symbol)
);
```

### positions (NEW)

```sql
CREATE TABLE positions (
    id              SERIAL PRIMARY KEY,
    symbol          VARCHAR(10) NOT NULL,
    exchange        VARCHAR(20),
    direction       VARCHAR(5) NOT NULL,               -- LONG or SHORT
    status          VARCHAR(10) NOT NULL DEFAULT 'OPEN', -- OPEN, CLOSED, EXPIRED

    -- Entry info (user-provided)
    entry_price     FLOAT NOT NULL,
    quantity        INTEGER NOT NULL,
    entry_time      TIMESTAMP NOT NULL,
    entry_signal_id INTEGER REFERENCES signals(id),    -- Which signal prompted this trade

    -- Exit strategy config at open time
    stop_loss_price      FLOAT,
    profit_target_price  FLOAT,
    stop_loss_pct        FLOAT,
    profit_target_pct    FLOAT,
    use_atr_exits        BOOLEAN DEFAULT true,
    atr_stop_multiplier  FLOAT DEFAULT 1.5,
    atr_target_multiplier FLOAT DEFAULT 2.5,
    atr_value_at_entry   FLOAT,                        -- ATR(14) at entry time
    eod_exit_enabled     BOOLEAN DEFAULT true,
    max_hold_bars        INTEGER DEFAULT 60,

    -- Live tracking (updated continuously)
    current_price        FLOAT,
    unrealized_pnl       FLOAT,
    unrealized_pnl_pct   FLOAT,
    high_since_entry     FLOAT,                        -- For potential trailing stop
    low_since_entry      FLOAT,
    bars_held            INTEGER DEFAULT 0,
    last_updated         TIMESTAMP,

    -- Exit info (filled on close)
    exit_price      FLOAT,
    exit_time       TIMESTAMP,
    exit_reason     VARCHAR(30),                       -- stop_loss, profit_target, indicator_reversal,
                                                       -- sentiment_shift, eod_exit, manual, max_hold
    exit_signal_id  INTEGER REFERENCES exit_signals(id),
    realized_pnl    FLOAT,
    realized_pnl_pct FLOAT,
    realized_pnl_dollar FLOAT,

    -- Context
    regime_at_entry VARCHAR(30),
    regime_at_exit  VARCHAR(30),
    config_snapshot_id INTEGER REFERENCES parameter_snapshots(id),

    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_positions_status ON positions(status);
CREATE INDEX idx_positions_symbol ON positions(symbol, status);
```

### exit_signals (NEW)

```sql
CREATE TABLE exit_signals (
    id              SERIAL PRIMARY KEY,
    position_id     INTEGER NOT NULL REFERENCES positions(id),
    symbol          VARCHAR(10) NOT NULL,
    exit_type       VARCHAR(30) NOT NULL,              -- stop_loss, profit_target,
                                                       -- indicator_reversal, sentiment_shift,
                                                       -- eod_warning, max_hold_warning
    urgency         VARCHAR(10) NOT NULL,              -- critical, high, medium, low
    trigger_price   FLOAT,
    current_price   FLOAT NOT NULL,
    message         TEXT NOT NULL,                      -- Human-readable alert
    details         JSONB,                              -- Extra context (indicator values, news, etc.)
    acknowledged    BOOLEAN DEFAULT false,              -- User has seen this
    acted_on        BOOLEAN DEFAULT false,              -- User closed the position
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_exit_signals_position ON exit_signals(position_id, created_at DESC);
CREATE INDEX idx_exit_signals_unacked ON exit_signals(acknowledged) WHERE acknowledged = false;
```

### signals (updated)

```sql
CREATE TABLE signals (
    id              SERIAL PRIMARY KEY,
    symbol          VARCHAR(10) NOT NULL,
    signal_type     VARCHAR(4) NOT NULL,
    conviction      FLOAT NOT NULL,
    tech_score      FLOAT NOT NULL,
    sentiment_score FLOAT NOT NULL,
    fundamental_score FLOAT NOT NULL,
    price_at_signal FLOAT NOT NULL,
    regime_at_signal VARCHAR(30),
    config_snapshot_id INTEGER REFERENCES parameter_snapshots(id),
    reasons         JSONB,

    -- Suggested exit levels (NEW)
    suggested_stop_loss    FLOAT,
    suggested_profit_target FLOAT,
    atr_at_signal          FLOAT,

    created_at      TIMESTAMP DEFAULT NOW(),

    -- Outcome tracking
    outcome         VARCHAR(10),
    exit_price      FLOAT,
    return_pct      FLOAT,
    bars_held       INTEGER,
    outcome_at      TIMESTAMP
);
```

### parameter_snapshots / regime_log / meta_reviews / daily_performance

Same as previous doc, with `meta_reviews` now including `exit_strategy_assessment` in its JSONB fields.

---

## Implementation Guide

Build in this order. Each phase produces a working system.

---

### Phase 1: Core Backend + API

Port the signal engine to Python/FastAPI. Same as before: `engine/indicators.py` (EMA, RSI, MACD), `engine/analyzer.py` (conviction scoring), `engine/data_provider.py` (simulated + real).

**New in analyzer.py:** When generating a BUY/SELL signal, also compute and attach suggested exit levels:

```python
def compute_suggested_exits(bars: list[dict], entry_price: float, 
                            direction: str, config: dict) -> dict:
    """
    Computes ATR-based stop loss and profit target suggestions.
    Attached to every BUY/SELL signal so the user sees them immediately.
    """
    highs = np.array([b["high"] for b in bars[-14:]])
    lows = np.array([b["low"] for b in bars[-14:]])
    closes = np.array([b["close"] for b in bars[-15:-1]])

    # ATR(14)
    tr = np.maximum(highs - lows,
                    np.maximum(np.abs(highs - closes), np.abs(lows - closes)))
    atr = float(np.mean(tr))

    stop_mult = config.get("atr_stop_multiplier", 1.5)
    target_mult = config.get("atr_target_multiplier", 2.5)

    if direction == "LONG":
        stop_loss = entry_price - atr * stop_mult
        profit_target = entry_price + atr * target_mult
    else:  # SHORT
        stop_loss = entry_price + atr * stop_mult
        profit_target = entry_price - atr * target_mult

    return {
        "suggested_stop_loss": round(stop_loss, 2),
        "suggested_profit_target": round(profit_target, 2),
        "atr_at_signal": round(atr, 4),
        "risk_reward_ratio": round(target_mult / stop_mult, 2),
    }
```

---

### Phase 2: Stock Discovery

**Universe management** (S&P 500, NASDAQ 100, TSX/TSXV), **pre-market screener** (5:00 AM, scans ~830 stocks, scores on 6 dimensions, surfaces top 30), **AI watchlist builder** (6:00 AM, Claude picks 12 stocks with reasoning).

Same implementation as previous doc — see `discovery/universe/`, `discovery/screener/`, `discovery/ai_watchlist/`.

---

### Phase 3: Position Management System

This is the core new feature — tracking open trades and generating exit signals.

#### 3.1 — Position Manager

**`positions/manager.py`**

```python
from datetime import datetime
from app.models.position import Position
from app.models.exit_signal import ExitSignal
from app.positions.exit_strategies.composite import CompositeExitStrategy

class PositionManager:
    """
    Manages the lifecycle of trading positions.
    
    Flow:
    1. User opens position (manual entry via API/UI)
    2. System attaches exit strategy config (from current params + regime)
    3. Position monitor continuously evaluates exit conditions
    4. Exit signals pushed to user via WebSocket + email
    5. User closes position (manual via API/UI)
    6. Outcome recorded → feeds back into optimizer
    """

    def __init__(self, db, data_provider, exit_strategy, notification_service):
        self.db = db
        self.data = data_provider
        self.exit_strategy = exit_strategy
        self.notifications = notification_service

    async def open_position(self, trade_input: dict) -> Position:
        """
        User manually enters a trade.
        
        Required: symbol, direction (LONG/SHORT), entry_price, quantity
        Optional: entry_signal_id, custom stop/target overrides
        """
        symbol = trade_input["symbol"]
        entry_price = trade_input["entry_price"]
        direction = trade_input["direction"]

        # Get current ATR for dynamic exit levels
        bars = await self.data.get_intraday(symbol)
        atr = self._calc_atr(bars, 14)

        # Get current config for exit defaults
        config = await get_current_config(self.db)
        regime = await get_current_regime(self.db)

        # Compute exit levels
        stop_mult = config.get("atr_stop_multiplier", 1.5)
        target_mult = config.get("atr_target_multiplier", 2.5)

        if direction == "LONG":
            default_stop = entry_price - atr * stop_mult
            default_target = entry_price + atr * target_mult
        else:
            default_stop = entry_price + atr * stop_mult
            default_target = entry_price - atr * target_mult

        position = Position(
            symbol=symbol,
            exchange=trade_input.get("exchange"),
            direction=direction,
            status="OPEN",
            entry_price=entry_price,
            quantity=trade_input["quantity"],
            entry_time=trade_input.get("entry_time", datetime.utcnow()),
            entry_signal_id=trade_input.get("entry_signal_id"),

            # Exit config — user can override these
            stop_loss_price=trade_input.get("stop_loss_price", round(default_stop, 2)),
            profit_target_price=trade_input.get("profit_target_price", round(default_target, 2)),
            stop_loss_pct=trade_input.get("stop_loss_pct", config.get("default_stop_loss_pct", 2.0)),
            profit_target_pct=trade_input.get("profit_target_pct", config.get("default_profit_target_pct", 3.0)),
            use_atr_exits=trade_input.get("use_atr_exits", True),
            atr_stop_multiplier=stop_mult,
            atr_target_multiplier=target_mult,
            atr_value_at_entry=round(atr, 4),
            eod_exit_enabled=trade_input.get("eod_exit_enabled", True),
            max_hold_bars=trade_input.get("max_hold_bars", config.get("max_hold_bars", 60)),

            # Initial tracking
            current_price=entry_price,
            unrealized_pnl=0.0,
            unrealized_pnl_pct=0.0,
            high_since_entry=entry_price,
            low_since_entry=entry_price,
            bars_held=0,

            # Context
            regime_at_entry=regime.regime if regime else None,
            config_snapshot_id=await get_current_config_id(self.db),
        )

        self.db.add(position)
        await self.db.commit()
        await self.db.refresh(position)

        return position

    async def close_position(self, position_id: int, exit_price: float,
                              exit_reason: str = "manual") -> Position:
        """User manually closes a position, or called by exit alert acceptance."""
        position = await self.db.get(Position, position_id)
        if not position or position.status != "OPEN":
            raise ValueError("Position not found or already closed")

        regime = await get_current_regime(self.db)

        if position.direction == "LONG":
            pnl_pct = (exit_price - position.entry_price) / position.entry_price * 100
        else:
            pnl_pct = (position.entry_price - exit_price) / position.entry_price * 100

        pnl_dollar = pnl_pct / 100 * position.entry_price * position.quantity

        position.status = "CLOSED"
        position.exit_price = exit_price
        position.exit_time = datetime.utcnow()
        position.exit_reason = exit_reason
        position.realized_pnl = round(pnl_pct, 4)
        position.realized_pnl_pct = round(pnl_pct, 4)
        position.realized_pnl_dollar = round(pnl_dollar, 2)
        position.regime_at_exit = regime.regime if regime else None

        await self.db.commit()

        # Feed outcome into signal record if linked
        if position.entry_signal_id:
            await self._update_signal_outcome(position)

        return position

    async def get_open_positions(self) -> list[Position]:
        """Returns all currently open positions."""
        result = await self.db.execute(
            select(Position).where(Position.status == "OPEN")
        )
        return result.scalars().all()

    async def get_trade_history(self, days: int = 30) -> list[Position]:
        """Returns closed positions within date range."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        result = await self.db.execute(
            select(Position)
            .where(Position.status == "CLOSED", Position.exit_time >= cutoff)
            .order_by(Position.exit_time.desc())
        )
        return result.scalars().all()

    def _calc_atr(self, bars, period=14):
        if len(bars) < period + 1:
            return abs(bars[-1]["high"] - bars[-1]["low"])
        trs = []
        for i in range(-period, 0):
            tr = max(bars[i]["high"] - bars[i]["low"],
                     abs(bars[i]["high"] - bars[i-1]["close"]),
                     abs(bars[i]["low"] - bars[i-1]["close"]))
            trs.append(tr)
        return sum(trs) / len(trs)
```

#### 3.2 — Exit Strategy Interface

**`positions/exit_strategies/base.py`**

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

class ExitUrgency(str, Enum):
    CRITICAL = "critical"   # Exit NOW — stop loss hit, circuit breaker
    HIGH = "high"           # Exit soon — target hit, strong reversal
    MEDIUM = "medium"       # Consider exiting — indicator weakening
    LOW = "low"             # Heads up — sentiment shifting, time warning

@dataclass
class ExitSignalResult:
    triggered: bool
    exit_type: str           # stop_loss, profit_target, indicator_reversal, etc.
    urgency: ExitUrgency
    trigger_price: float | None
    current_price: float
    message: str             # Human-readable alert
    details: dict            # Extra context

class ExitStrategy(ABC):
    @abstractmethod
    async def evaluate(self, position, current_bar: dict,
                       recent_bars: list[dict]) -> ExitSignalResult | None:
        """Evaluate whether this exit condition is triggered."""
        ...
```

#### 3.3 — Stop Loss

**`positions/exit_strategies/stop_loss.py`**

```python
class StopLossStrategy(ExitStrategy):
    """
    Fixed price or ATR-based stop loss.
    
    Triggers CRITICAL urgency — this means "get out now, you're losing money."
    
    Modes:
    - Fixed price: position.stop_loss_price (set at entry)
    - Fixed percentage: position.stop_loss_pct below entry
    - ATR-based: entry - (ATR × multiplier)
    
    The system uses the TIGHTEST (most protective) of all configured stops.
    """

    async def evaluate(self, position, current_bar, recent_bars) -> ExitSignalResult | None:
        price = current_bar["close"]
        entry = position.entry_price
        is_long = position.direction == "LONG"

        # Collect all stop levels
        stops = []

        # Fixed price stop
        if position.stop_loss_price:
            stops.append(position.stop_loss_price)

        # Percentage stop
        if position.stop_loss_pct:
            if is_long:
                stops.append(entry * (1 - position.stop_loss_pct / 100))
            else:
                stops.append(entry * (1 + position.stop_loss_pct / 100))

        if not stops:
            return None

        # Use tightest stop
        if is_long:
            stop_level = max(stops)  # Highest stop = tightest for long
            triggered = price <= stop_level
        else:
            stop_level = min(stops)  # Lowest stop = tightest for short
            triggered = price >= stop_level

        if triggered:
            loss_pct = abs(price - entry) / entry * 100
            return ExitSignalResult(
                triggered=True,
                exit_type="stop_loss",
                urgency=ExitUrgency.CRITICAL,
                trigger_price=stop_level,
                current_price=price,
                message=f"STOP LOSS HIT on {position.symbol} — "
                        f"Price ${price:.2f} breached stop at ${stop_level:.2f} "
                        f"(loss: {loss_pct:.2f}%). Exit immediately.",
                details={
                    "stop_level": stop_level,
                    "entry_price": entry,
                    "loss_pct": round(loss_pct, 2),
                },
            )

        # Warning if approaching stop (within 30% of distance)
        if is_long:
            distance = price - stop_level
            total_distance = entry - stop_level
        else:
            distance = stop_level - price
            total_distance = stop_level - entry

        if total_distance > 0 and distance / total_distance < 0.3:
            return ExitSignalResult(
                triggered=True,
                exit_type="stop_loss",
                urgency=ExitUrgency.MEDIUM,
                trigger_price=stop_level,
                current_price=price,
                message=f"WARNING: {position.symbol} approaching stop loss — "
                        f"Price ${price:.2f}, stop at ${stop_level:.2f}",
                details={"distance_remaining_pct": round(distance / total_distance * 100, 1)},
            )

        return None
```

#### 3.4 — Profit Target

**`positions/exit_strategies/profit_target.py`**

```python
class ProfitTargetStrategy(ExitStrategy):
    """
    Fixed price or ATR-based profit target.
    
    Triggers HIGH urgency — "You've hit your target, take profits."
    
    Also fires at partial levels (50% and 75% of target) as LOW urgency
    informational alerts so user can decide to take partial profits.
    """

    async def evaluate(self, position, current_bar, recent_bars) -> ExitSignalResult | None:
        price = current_bar["close"]
        entry = position.entry_price
        is_long = position.direction == "LONG"

        targets = []
        if position.profit_target_price:
            targets.append(position.profit_target_price)
        if position.profit_target_pct:
            if is_long:
                targets.append(entry * (1 + position.profit_target_pct / 100))
            else:
                targets.append(entry * (1 - position.profit_target_pct / 100))

        if not targets:
            return None

        if is_long:
            target_level = min(targets)  # Conservative target for long
            triggered = price >= target_level
            gain_pct = (price - entry) / entry * 100
        else:
            target_level = max(targets)
            triggered = price <= target_level
            gain_pct = (entry - price) / entry * 100

        if triggered:
            return ExitSignalResult(
                triggered=True,
                exit_type="profit_target",
                urgency=ExitUrgency.HIGH,
                trigger_price=target_level,
                current_price=price,
                message=f"TARGET HIT on {position.symbol} — "
                        f"Price ${price:.2f} reached target ${target_level:.2f} "
                        f"(gain: +{gain_pct:.2f}%). Consider taking profits.",
                details={
                    "target_level": target_level,
                    "gain_pct": round(gain_pct, 2),
                    "risk_reward_achieved": round(
                        gain_pct / position.stop_loss_pct if position.stop_loss_pct else 0, 2
                    ),
                },
            )

        # Partial target alerts (50% and 75%)
        total_distance = abs(target_level - entry)
        current_distance = abs(price - entry)
        if total_distance > 0:
            progress = current_distance / total_distance
            if progress >= 0.75 and gain_pct > 0:
                return ExitSignalResult(
                    triggered=True,
                    exit_type="profit_target",
                    urgency=ExitUrgency.LOW,
                    trigger_price=target_level,
                    current_price=price,
                    message=f"{position.symbol} at 75% of profit target — "
                            f"+{gain_pct:.2f}% (target: ${target_level:.2f})",
                    details={"progress_pct": 75, "gain_pct": round(gain_pct, 2)},
                )

        return None
```

#### 3.5 — Indicator Reversal Exit

**`positions/exit_strategies/indicator_reversal.py`**

```python
class IndicatorReversalStrategy(ExitStrategy):
    """
    Exits when the same technical indicators that triggered entry now flip.
    
    For a LONG position, fires when:
    - RSI crosses above overbought (was oversold at entry)
    - EMA fast crosses below slow (bearish cross)
    - MACD histogram flips from positive to negative
    
    Uses a scoring system — single indicator flip = MEDIUM urgency,
    multiple indicators flipping = HIGH urgency.
    """

    def __init__(self, config: dict):
        self.config = config

    async def evaluate(self, position, current_bar, recent_bars) -> ExitSignalResult | None:
        if len(recent_bars) < 2:
            return None

        is_long = position.direction == "LONG"
        closes = np.array([b["close"] for b in recent_bars])

        # Compute current indicators
        rsi = calc_rsi(closes, self.config.get("rsi_period", 14))
        ema_fast = calc_ema(closes, self.config.get("ema_fast", 9))
        ema_slow = calc_ema(closes, self.config.get("ema_slow", 21))
        macd_line, signal_line, histogram = calc_macd(
            closes, self.config.get("macd_fast", 12),
            self.config.get("macd_slow", 26), self.config.get("macd_signal", 9)
        )

        current_rsi = rsi[-1]
        prev_rsi = rsi[-2]
        reversal_signals = []
        reversal_score = 0

        if is_long:
            # RSI overbought exit
            if current_rsi > self.config.get("rsi_overbought", 70):
                reversal_signals.append(f"RSI overbought ({current_rsi:.0f})")
                reversal_score += 1

            # EMA bearish cross
            if ema_fast[-1] < ema_slow[-1] and ema_fast[-2] >= ema_slow[-2]:
                reversal_signals.append("EMA bearish crossover")
                reversal_score += 1.5

            # MACD bearish flip
            if histogram[-1] < 0 and histogram[-2] >= 0:
                reversal_signals.append("MACD bearish flip")
                reversal_score += 1.5

            # EMA trend reversal (fast below slow)
            if ema_fast[-1] < ema_slow[-1]:
                reversal_signals.append("Below EMA trend")
                reversal_score += 0.5

        else:  # SHORT position
            if current_rsi < self.config.get("rsi_oversold", 30):
                reversal_signals.append(f"RSI oversold ({current_rsi:.0f})")
                reversal_score += 1

            if ema_fast[-1] > ema_slow[-1] and ema_fast[-2] <= ema_slow[-2]:
                reversal_signals.append("EMA bullish crossover")
                reversal_score += 1.5

            if histogram[-1] > 0 and histogram[-2] <= 0:
                reversal_signals.append("MACD bullish flip")
                reversal_score += 1.5

        if reversal_score == 0:
            return None

        urgency = ExitUrgency.HIGH if reversal_score >= 2.5 else ExitUrgency.MEDIUM

        return ExitSignalResult(
            triggered=True,
            exit_type="indicator_reversal",
            urgency=urgency,
            trigger_price=None,
            current_price=current_bar["close"],
            message=f"INDICATOR REVERSAL on {position.symbol} — "
                    f"{', '.join(reversal_signals)}. "
                    f"Reversal score: {reversal_score:.1f}/4",
            details={
                "reversal_signals": reversal_signals,
                "reversal_score": reversal_score,
                "rsi": round(current_rsi, 1),
                "ema_fast": round(ema_fast[-1], 2),
                "ema_slow": round(ema_slow[-1], 2),
                "macd_hist": round(histogram[-1], 4),
            },
        )
```

#### 3.6 — Sentiment Shift Exit

**`positions/exit_strategies/sentiment_shift.py`**

```python
class SentimentShiftStrategy(ExitStrategy):
    """
    Monitors for breaking negative news on stocks you hold long
    (or positive news on stocks you hold short).
    
    Fires when:
    - New high-impact negative headline appears (impact < -0.5)
    - Sentiment score drops significantly from entry sentiment
    - Multiple negative headlines cluster in short time
    
    This catches things indicators can't: lawsuits, earnings warnings,
    executive departures, product recalls.
    """

    def __init__(self, news_service, sentiment_engine):
        self.news = news_service
        self.sentiment = sentiment_engine

    async def evaluate(self, position, current_bar, recent_bars) -> ExitSignalResult | None:
        # Get headlines since position was opened
        headlines = await self.news.get_recent(
            position.symbol,
            since=position.entry_time
        )

        if not headlines:
            return None

        is_long = position.direction == "LONG"

        # Check for high-impact adverse headlines
        adverse_headlines = []
        for h in headlines:
            if is_long and h["impact"] < -0.5:
                adverse_headlines.append(h)
            elif not is_long and h["impact"] > 0.5:
                adverse_headlines.append(h)

        if not adverse_headlines:
            return None

        worst = min(adverse_headlines, key=lambda h: h["impact"]) if is_long \
                else max(adverse_headlines, key=lambda h: h["impact"])

        # Determine urgency based on impact severity
        impact = abs(worst["impact"])
        if impact > 0.7 or len(adverse_headlines) >= 3:
            urgency = ExitUrgency.HIGH
        else:
            urgency = ExitUrgency.MEDIUM

        direction_word = "negative" if is_long else "positive"

        return ExitSignalResult(
            triggered=True,
            exit_type="sentiment_shift",
            urgency=urgency,
            trigger_price=None,
            current_price=current_bar["close"],
            message=f"SENTIMENT SHIFT on {position.symbol} — "
                    f"{len(adverse_headlines)} {direction_word} headline(s) detected. "
                    f"Worst: \"{worst['headline'][:80]}\" (impact: {worst['impact']:.2f})",
            details={
                "adverse_count": len(adverse_headlines),
                "worst_headline": worst["headline"],
                "worst_impact": worst["impact"],
                "worst_category": worst.get("category"),
            },
        )
```

#### 3.7 — Time-Based Exit

**`positions/exit_strategies/time_based.py`**

```python
from datetime import datetime, time
import pytz

class TimeBasedExitStrategy(ExitStrategy):
    """
    Two time-based exit conditions:
    
    1. EOD Warning: Fires 15 minutes before market close (3:45 PM ET)
       telling user to close all positions to avoid overnight risk.
       Urgency: HIGH at 3:45 PM, CRITICAL at 3:55 PM.
    
    2. Max Hold Time: Fires when position has been open for N bars.
       Prevents "set and forget" — if a trade hasn't worked in 60 bars
       (5 hours at 5-min intervals), the thesis is probably wrong.
    """

    def __init__(self, timezone: str = "America/New_York",
                 eod_warning_minutes: int = 15):
        self.tz = pytz.timezone(timezone)
        self.eod_warning_minutes = eod_warning_minutes
        self.market_close = time(16, 0)

    async def evaluate(self, position, current_bar, recent_bars) -> ExitSignalResult | None:
        now = datetime.now(self.tz)
        close_time = now.replace(hour=16, minute=0, second=0)
        minutes_to_close = (close_time - now).total_seconds() / 60

        # EOD Warning
        if position.eod_exit_enabled and 0 < minutes_to_close <= self.eod_warning_minutes:
            urgency = ExitUrgency.CRITICAL if minutes_to_close <= 5 else ExitUrgency.HIGH

            pnl_pct = position.unrealized_pnl_pct or 0

            return ExitSignalResult(
                triggered=True,
                exit_type="eod_warning",
                urgency=urgency,
                trigger_price=None,
                current_price=current_bar["close"],
                message=f"EOD EXIT WARNING — {position.symbol} still open, "
                        f"{minutes_to_close:.0f} min to close. "
                        f"Current P&L: {pnl_pct:+.2f}%. "
                        f"{'Close to avoid overnight risk.' if urgency == ExitUrgency.CRITICAL else 'Consider closing.'}",
                details={
                    "minutes_to_close": round(minutes_to_close),
                    "current_pnl_pct": round(pnl_pct, 2),
                },
            )

        # Max hold time
        if position.max_hold_bars and position.bars_held >= position.max_hold_bars:
            return ExitSignalResult(
                triggered=True,
                exit_type="max_hold_warning",
                urgency=ExitUrgency.MEDIUM,
                trigger_price=None,
                current_price=current_bar["close"],
                message=f"MAX HOLD TIME reached on {position.symbol} — "
                        f"Open for {position.bars_held} bars ({position.bars_held * 5} min). "
                        f"Original thesis may no longer apply.",
                details={
                    "bars_held": position.bars_held,
                    "max_bars": position.max_hold_bars,
                    "minutes_held": position.bars_held * 5,
                },
            )

        return None
```

#### 3.8 — Composite Exit Engine

**`positions/exit_strategies/composite.py`**

```python
class CompositeExitStrategy:
    """
    Runs all exit strategies in parallel on every position,
    deduplicates alerts, and ranks by urgency.
    
    Priority order:
    1. CRITICAL: Stop loss hit, EOD < 5 min
    2. HIGH: Profit target hit, strong indicator reversal, EOD warning
    3. MEDIUM: Partial indicator reversal, approaching stop, max hold
    4. LOW: Partial target progress, mild sentiment shift
    
    Deduplication: only fires the same exit_type once per position
    within a cooldown window (default 5 min) to avoid spam.
    """

    def __init__(self, strategies: list[ExitStrategy], cooldown_minutes: int = 5):
        self.strategies = strategies
        self.cooldown_minutes = cooldown_minutes
        self.recent_alerts = {}  # (position_id, exit_type) → last_fired_time

    async def evaluate_all(self, position, current_bar, recent_bars) -> list[ExitSignalResult]:
        """Run all strategies, return list of triggered signals sorted by urgency."""
        results = []

        for strategy in self.strategies:
            try:
                result = await strategy.evaluate(position, current_bar, recent_bars)
                if result and result.triggered:
                    # Check cooldown
                    key = (position.id, result.exit_type)
                    last_fired = self.recent_alerts.get(key)
                    if last_fired:
                        elapsed = (datetime.utcnow() - last_fired).total_seconds() / 60
                        if elapsed < self.cooldown_minutes:
                            continue

                    self.recent_alerts[key] = datetime.utcnow()
                    results.append(result)

            except Exception as e:
                # Log but don't crash — exit monitoring must stay up
                logger.error(f"Exit strategy error for {position.symbol}: {e}")

        # Sort by urgency priority
        urgency_order = {
            ExitUrgency.CRITICAL: 0,
            ExitUrgency.HIGH: 1,
            ExitUrgency.MEDIUM: 2,
            ExitUrgency.LOW: 3,
        }
        results.sort(key=lambda r: urgency_order[r.urgency])

        return results
```

#### 3.9 — Position Monitor

**`positions/monitor.py`**

```python
class PositionMonitor:
    """
    Continuously monitors all open positions and generates exit alerts.
    
    Runs as a Celery task every 30 seconds during market hours.
    
    For each open position:
    1. Fetch latest price data
    2. Update position tracking fields (current_price, unrealized P&L, high/low since entry)
    3. Run all exit strategies
    4. Save triggered exit signals to database
    5. Push alerts via WebSocket + notifications
    """

    def __init__(self, position_manager, composite_exit, data_provider,
                 notification_service, websocket_manager):
        self.positions = position_manager
        self.exit_engine = composite_exit
        self.data = data_provider
        self.notifications = notification_service
        self.ws = websocket_manager

    async def check_all_positions(self):
        """Main monitoring loop — called every 30 seconds."""
        open_positions = await self.positions.get_open_positions()

        for position in open_positions:
            try:
                await self._check_position(position)
            except Exception as e:
                logger.error(f"Monitor error for position {position.id}: {e}")

    async def _check_position(self, position):
        # 1. Get latest bars
        bars = await self.data.get_intraday(position.symbol)
        if not bars:
            return

        current_bar = bars[-1]
        price = current_bar["close"]

        # 2. Update position tracking
        is_long = position.direction == "LONG"
        if is_long:
            pnl_pct = (price - position.entry_price) / position.entry_price * 100
        else:
            pnl_pct = (position.entry_price - price) / position.entry_price * 100

        position.current_price = price
        position.unrealized_pnl = round(pnl_pct, 4)
        position.unrealized_pnl_pct = round(pnl_pct, 4)
        position.high_since_entry = max(position.high_since_entry or price, price)
        position.low_since_entry = min(position.low_since_entry or price, price)
        position.bars_held = (position.bars_held or 0) + 1
        position.last_updated = datetime.utcnow()

        await self.db.commit()

        # 3. Run exit strategies
        exit_signals = await self.exit_engine.evaluate_all(position, current_bar, bars)

        # 4. Save and push alerts
        for signal in exit_signals:
            exit_record = ExitSignal(
                position_id=position.id,
                symbol=position.symbol,
                exit_type=signal.exit_type,
                urgency=signal.urgency.value,
                trigger_price=signal.trigger_price,
                current_price=signal.current_price,
                message=signal.message,
                details=signal.details,
            )
            self.db.add(exit_record)

            # Push via WebSocket
            await self.ws.broadcast({
                "type": "exit_alert",
                "position_id": position.id,
                "symbol": position.symbol,
                "urgency": signal.urgency.value,
                "exit_type": signal.exit_type,
                "message": signal.message,
                "current_price": signal.current_price,
            })

            # Email/push for CRITICAL and HIGH
            if signal.urgency in (ExitUrgency.CRITICAL, ExitUrgency.HIGH):
                await self.notifications.send_exit_alert(signal, position)

        await self.db.commit()
```

#### 3.10 — Position API Routes

**`api/positions.py`**

```python
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/positions", tags=["positions"])

@router.get("/", response_model=list[PositionResponse])
async def get_open_positions(manager=Depends(get_position_manager)):
    """List all open positions with live P&L."""
    return await manager.get_open_positions()

@router.post("/", response_model=PositionResponse)
async def open_position(trade: TradeInput, manager=Depends(get_position_manager)):
    """
    Manually enter a trade.
    
    Required: symbol, direction (LONG/SHORT), entry_price, quantity
    Optional: stop_loss_price, profit_target_price, eod_exit_enabled
    
    System auto-computes ATR-based stop/target if not provided.
    """
    return await manager.open_position(trade.dict())

@router.put("/{position_id}/close", response_model=PositionResponse)
async def close_position(position_id: int, close: CloseInput,
                          manager=Depends(get_position_manager)):
    """Manually close a position. Records outcome for optimizer."""
    return await manager.close_position(
        position_id, close.exit_price, close.exit_reason or "manual"
    )

@router.put("/{position_id}/update-exits")
async def update_exit_levels(position_id: int, exits: ExitUpdateInput,
                              manager=Depends(get_position_manager)):
    """Update stop loss / profit target on an open position."""
    return await manager.update_exit_levels(position_id, exits.dict())

@router.get("/{position_id}/exit-signals", response_model=list[ExitSignalResponse])
async def get_exit_signals(position_id: int, db=Depends(get_db)):
    """Get all exit signals generated for a position."""
    result = await db.execute(
        select(ExitSignal)
        .where(ExitSignal.position_id == position_id)
        .order_by(ExitSignal.created_at.desc())
    )
    return result.scalars().all()

@router.get("/history", response_model=list[PositionResponse])
async def get_trade_history(days: int = 30, manager=Depends(get_position_manager)):
    """Get closed trade history."""
    return await manager.get_trade_history(days)

@router.get("/stats", response_model=TradeStatsResponse)
async def get_trade_stats(days: int = 30, manager=Depends(get_position_manager)):
    """Get aggregate trade statistics."""
    trades = await manager.get_trade_history(days)
    return compute_trade_stats(trades)
```

#### 3.11 — Position Monitor Celery Task

**`tasks/position_monitor.py`**

```python
from app.tasks.celery_app import celery

@celery.task
def monitor_positions():
    """
    Runs every 30 seconds during market hours.
    Checks all open positions against exit strategies.
    """
    monitor = get_position_monitor()
    asyncio.run(monitor.check_all_positions())
```

---

### Phase 4: Adaptive Exit Optimization

The Layer 1 optimizer now tunes exit parameters too — not just entry parameters.

**Updated `adaptation/layer1_optimizer/parameter_space.py`:**

```python
PARAMETER_SPACE = [
    # Entry parameters
    ParamBound("rsi_period",            5,   30,  1,    14),
    ParamBound("rsi_overbought",        60,  90,  1,    70),
    ParamBound("rsi_oversold",          10,  40,  1,    30),
    ParamBound("ema_fast",              3,   20,  1,    9),
    ParamBound("ema_slow",              10,  50,  1,    21),
    ParamBound("volume_multiplier",     1.0, 3.0, 0.1,  1.5),
    ParamBound("min_signal_strength",   0.5, 4.0, 0.25, 2.0),
    ParamBound("technical_weight",      0.0, 1.0, 0.05, 0.5),
    ParamBound("sentiment_weight",      0.0, 1.0, 0.05, 0.3),
    ParamBound("fundamental_weight",    0.0, 1.0, 0.05, 0.2),

    # EXIT parameters (NEW — optimizer tunes these too)
    ParamBound("atr_stop_multiplier",   0.5, 3.0, 0.1,  1.5),
    ParamBound("atr_target_multiplier", 1.0, 5.0, 0.1,  2.5),
    ParamBound("default_stop_loss_pct", 0.5, 5.0, 0.25, 2.0),
    ParamBound("default_profit_target_pct", 1.0, 8.0, 0.25, 3.0),
    ParamBound("max_hold_bars",         20,  120, 5,    60),
]
```

**Updated `adaptation/layer2_regime/presets.py`** — Regime presets now include exit parameters:

```python
REGIME_PRESETS = {
    MarketRegime.TRENDING_UP: {
        # Entry params
        "rsi_oversold": 35, "rsi_overbought": 80,
        "min_signal_strength": 1.5, "technical_weight": 0.6,
        # Exit params — let winners run in trends
        "atr_target_multiplier": 3.0,   # Wider targets
        "atr_stop_multiplier": 1.5,     # Normal stops
        "max_hold_bars": 90,            # Hold longer
    },
    MarketRegime.TRENDING_DOWN: {
        "rsi_oversold": 25, "rsi_overbought": 65,
        "min_signal_strength": 2.5,
        # Exit params — tight stops, quick profits in downtrends
        "atr_target_multiplier": 2.0,   # Smaller targets
        "atr_stop_multiplier": 1.2,     # Tighter stops
        "max_hold_bars": 40,            # Don't hold long
    },
    MarketRegime.MEAN_REVERTING: {
        "rsi_oversold": 28, "rsi_overbought": 72,
        "min_signal_strength": 1.75,
        # Exit params — take profits at mean
        "atr_target_multiplier": 2.0,
        "atr_stop_multiplier": 1.5,
        "max_hold_bars": 50,
    },
    MarketRegime.VOLATILE_CHOPPY: {
        "rsi_oversold": 22, "rsi_overbought": 78,
        "min_signal_strength": 3.0,
        # Exit params — very tight in chop, take any profit
        "atr_target_multiplier": 1.5,   # Small targets
        "atr_stop_multiplier": 1.0,     # Very tight stops
        "max_hold_bars": 25,            # Get out fast
    },
    MarketRegime.LOW_VOLATILITY: {
        "rsi_oversold": 32, "rsi_overbought": 68,
        "min_signal_strength": 1.5,
        # Exit params — standard exits, low vol = reliable
        "atr_target_multiplier": 2.5,
        "atr_stop_multiplier": 1.5,
        "max_hold_bars": 60,
    },
}
```

**Updated Layer 3 meta-review** — Claude now evaluates exit performance:

```python
# Added to daily review prompt:
"""
### Exit Strategy Performance
- Trades closed by stop loss: {stop_loss_count} ({stop_loss_avg_loss:.2%} avg loss)
- Trades closed by profit target: {target_count} ({target_avg_gain:.2%} avg gain)
- Trades closed by indicator reversal: {reversal_count}
- Trades closed by sentiment shift: {sentiment_count}
- Trades closed by EOD: {eod_count}
- Trades closed manually: {manual_count}
- Average bars held (winners): {avg_bars_winners}
- Average bars held (losers): {avg_bars_losers}
- Current ATR stop multiplier: {atr_stop_mult}
- Current ATR target multiplier: {atr_target_mult}

Are the stop losses too tight (stopped out before move completes)?
Are the profit targets too wide (never hitting target)?
Is max hold time appropriate?
"""
```

---

### Phase 5: Frontend — Positions Tab

**`components/tabs/PositionsTab.tsx`** displays:

1. **Active Positions Panel**
   - Card for each open position showing: symbol, direction (LONG/SHORT), entry price, current price, unrealized P&L (color-coded), bars held, time in trade
   - Visual stop/target levels on a mini price chart (horizontal lines showing entry, stop, target with price action)
   - Live P&L bar that fills green (toward target) or red (toward stop)
   - Urgency badge if any exit signal is active
   - "Close Position" button on each card

2. **Exit Alert Feed** (real-time via WebSocket)
   - Scrollable feed of exit signals as they fire
   - Color-coded by urgency: red CRITICAL, orange HIGH, yellow MEDIUM, gray LOW
   - Each alert shows: time, symbol, exit type, message, current price
   - "Close Now" quick action button on each alert
   - "Dismiss" button to acknowledge without acting

3. **Trade Entry Form** (always visible)
   - Symbol (dropdown from today's watchlist + free text)
   - Direction: LONG / SHORT toggle
   - Entry price (auto-fills with last price)
   - Quantity
   - Stop loss price (auto-suggested based on ATR, editable)
   - Profit target price (auto-suggested, editable)
   - Risk/reward ratio display (updates as you adjust stop/target)
   - EOD exit toggle (default on)
   - "Open Position" button

4. **Trade History Table**
   - Sortable table of closed trades
   - Columns: date, symbol, direction, entry, exit, P&L%, P&L$, bars held, exit reason, regime
   - Summary stats at top: total trades, win rate, avg return, best/worst trade, profit factor
   - Cumulative P&L chart
   - Filter by: date range, symbol, exit reason, direction

**Updated Price Chart (`PriceChart.tsx`):**
When a position is open for the selected stock, the chart now shows:
- Green horizontal line at entry price
- Red horizontal line at stop loss level
- Blue horizontal line at profit target level
- Shaded green zone (entry → target) and red zone (entry → stop)
- Triangle marker at entry point

---

## Celery Beat Schedule (Complete)

```python
celery.conf.beat_schedule = {
    # Stock Discovery
    "premarket-scan": {
        "task": "app.tasks.premarket_scan.run_scan",
        "schedule": crontab(minute=0, hour=5, day_of_week="1-5"),
    },
    "watchlist-build": {
        "task": "app.tasks.watchlist_build.build_daily_watchlist",
        "schedule": crontab(minute=0, hour=6, day_of_week="1-5"),
    },

    # Position Monitoring (every 30 seconds during market hours)
    "position-monitor": {
        "task": "app.tasks.position_monitor.monitor_positions",
        "schedule": 30.0,  # Every 30 seconds
        # Note: task itself checks if market is open before running
    },

    # Regime Detection
    "regime-detection": {
        "task": "app.tasks.regime_detection.run_regime_detection",
        "schedule": crontab(minute="*/30", hour="9-16", day_of_week="1-5"),
    },

    # Daily Wrap-up
    "daily-meta-review": {
        "task": "app.tasks.daily_meta_review.run_daily_meta_review",
        "schedule": crontab(minute=15, hour=16, day_of_week="1-5"),
    },
    "daily-performance": {
        "task": "app.tasks.performance_calc.calc_daily_performance",
        "schedule": crontab(minute=30, hour=16, day_of_week="1-5"),
    },

    # Maintenance
    "weekly-regime-retrain": {
        "task": "app.tasks.regime_detection.retrain_regime_model",
        "schedule": crontab(minute=0, hour=2, day_of_week="6"),
    },
    "weekly-universe-update": {
        "task": "app.tasks.universe_update.refresh_all_universes",
        "schedule": crontab(minute=0, hour=3, day_of_week="0"),
    },
}
```

---

## Daily Pipeline Timeline (Complete)

```
  5:00 AM  ─  Pre-market Screener scans ~830 stocks
  6:00 AM  ─  Claude builds personalized watchlist (12 picks)
              → Email: "Your watchlist is ready"
  
  9:30 AM  ─  Market Open
              ├── Signal engine starts scanning watchlist (every 5 min)
              ├── Position monitor activates (every 30 sec)
              └── First regime check
  
  Ongoing   ─  ENTRY signals fire on watchlist stocks
              → Browser + email alert: "BUY NVDA at $920, stop $910, target $940"
              → You enter the trade on Wealthsimple
              → You log it in Signal Terminal (entry price, quantity)
  
  Ongoing   ─  EXIT signals fire on open positions
              → CRITICAL: "STOP LOSS HIT on NVDA at $910 — exit immediately"
              → HIGH: "TARGET HIT on AAPL at $195 — +2.3% gain"
              → HIGH: "INDICATOR REVERSAL on AMD — EMA bearish cross + MACD flip"
              → MEDIUM: "SENTIMENT SHIFT on TSLA — downgrade from Goldman Sachs"
              → You close the trade on Wealthsimple
              → You log exit in Signal Terminal
  
  Every 30m ─  Regime detection runs
              → May switch parameter + exit presets
  
  Per trade ─  Layer 1 optimizer updates after each closed position
              → Tunes BOTH entry AND exit parameters
  
  3:45 PM   ─  EOD exit warnings on all open positions
              → "AAPL still open, 15 min to close. P&L: +1.2%"
  
  3:55 PM   ─  CRITICAL EOD alerts
              → "5 min to close — exit all positions"
  
  4:00 PM   ─  Market Close
  4:15 PM   ─  Claude daily meta-review
              → Reviews entries, exits, regime accuracy, watchlist quality
              → Email: daily performance report
  4:30 PM   ─  Performance calculation
```

---

## Docker Compose

```yaml
version: "3.9"

services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [db, redis]
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes: [./backend:/app]

  celery-worker:
    build: ./backend
    env_file: .env
    depends_on: [db, redis]
    command: celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4

  celery-beat:
    build: ./backend
    env_file: .env
    depends_on: [db, redis]
    command: celery -A app.tasks.celery_app beat --loglevel=info

  frontend:
    build: ./frontend
    ports: ["5173:5173"]
    volumes: [./frontend:/app, /app/node_modules]
    command: npm run dev -- --host

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: signal_terminal
      POSTGRES_USER: signal
      POSTGRES_PASSWORD: signal
    ports: ["5432:5432"]
    volumes: [pgdata:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

volumes:
  pgdata:
```

---

## Makefile

```makefile
.PHONY: dev up down migrate test seed seed-universe backtest train-regime scan watchlist logs

dev:         docker compose up --build
up:          docker compose up -d
down:        docker compose down
migrate:     cd backend && alembic upgrade head
test:        cd backend && pytest tests/ -v
seed-universe: cd backend && python scripts/seed_universe.py
seed:        cd backend && python scripts/seed_historical.py
backtest:    cd backend && python scripts/backtest.py
train-regime: cd backend && python scripts/train_regime_model.py
scan:        cd backend && python -c "from app.tasks.premarket_scan import run_scan; run_scan()"
watchlist:   cd backend && python -c "from app.tasks.watchlist_build import build_daily_watchlist; build_daily_watchlist()"
logs:        docker compose logs -f backend celery-worker
```

---

## Cold Start Procedure

1. `make seed-universe` — Populate S&P 500, NASDAQ 100, TSX (~830 stocks)
2. `make seed` — Generate 6–12 months simulated history
3. `make train-regime` — Train HMM on historical features
4. `make backtest` — Backtest strategy, populate initial signal outcomes
5. `make dev` — Start full system
6. First morning: screener at 5 AM, watchlist at 6 AM, ready by 9:30 AM
7. After 1–2 weeks: optimizer has enough live data, personalizer learns your patterns

---

## Wealthsimple Workflow

```
Signal Terminal                          Wealthsimple App
─────────────                           ────────────────
                                        
6:00 AM  Watchlist email ──────────→    Review picks
                                        
9:30 AM  BUY signal fires ─────────→   Execute trade
         (includes stop + target)       
                                        
         ←──────────────────────────    Enter in Signal Terminal:
         Log trade (price, qty)          symbol, price, quantity
                                        
Ongoing  EXIT alert fires ─────────→   Close trade
         (stop/target/reversal)          
                                        
         ←──────────────────────────    Enter exit in Signal Terminal:
         Log exit (price, reason)        exit price
                                        
4:15 PM  Daily review email ───────→   Review performance
```

---

## Disclaimer

This system is for **educational and informational purposes only**. It does not constitute financial advice. No trading system can guarantee profits. Markets are inherently unpredictable. Always do your own research, consult a licensed financial advisor, and only trade with money you can afford to lose. Past performance does not guarantee future results.
