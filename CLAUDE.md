# Signal Terminal — CLAUDE.md

> This file is loaded automatically into every Claude Code session.
> Keep it up to date as the project evolves.

---

## What This Is

A self-adapting swing trading signals platform. The user executes trades manually on Wealthsimple; Signal Terminal provides the intelligence layer:
- Daily watchlist (Claude-curated, 20 picks from ~4,700 stocks)
- Daily BUY/SELL signals with conviction scores (based on daily bars)
- EXIT alerts on open positions (stop loss, trailing stop, profit target, indicator reversal, sentiment shift)
- Self-tuning via 3-layer adaptive system (Bayesian optimizer + regime detection + Claude meta-review)
- Positions held for days to weeks (swing trading)

**Disclaimer:** Educational/informational only. Not financial advice.

Original spec (archived, may be outdated): `SIGNAL-TERMINAL-SPEC-ORIGINAL.md`

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Recharts, Tailwind CSS |
| Backend | Python 3.11+, FastAPI, Uvicorn |
| ML/Stats | scikit-learn, scipy, numpy, pandas, hmmlearn |
| AI Agent | Anthropic Claude API (`claude-sonnet-4-6` or latest Sonnet) |
| Database | PostgreSQL 16 + SQLAlchemy (async) + Alembic |
| Cache | Redis |
| Task Queue | Celery + Redis (beat scheduler) |
| WebSocket | FastAPI WebSocket |
| Notifications | Resend (email), Web Push API |
| Market Data | Massive.com (US OHLCV + news sentiment) + yfinance (TSX) + Finnhub (fundamentals + .TO news) |
| DevOps | Docker Compose, GitHub Actions |

---

## Build Phases

Build one phase at a time. Validate before moving on.

| # | Phase | Status | Notes |
|---|---|---|---|
| 1 | Core Backend — FastAPI skeleton, DB models, signal engine, simulated data provider | `DONE` | Ports: PostgreSQL 5555, Redis 6380 |
| 2 | Frontend Shell — React app, layout, Watchlist sidebar, Detail panel, wired to Phase 1 | `DONE` | Node 20+ required, WebSocket live signal feed still polling |
| 3 | Stock Discovery — Universe mgmt, pre-market screener, Claude AI watchlist builder | `DONE` | Needs ANTHROPIC_API_KEY for AI picks, fallback works without |
| 4 | Position Management — Open/close trades, exit strategy engine (6 strategies), WebSocket alerts | `DONE` | 6 exit strategies (incl. trailing stop) + WebSocket broadcast + full frontend UI |
| 5 | Adaptation — Layer 1 Bayesian optimizer, Layer 2 HMM regime detector, Layer 3 Claude meta-review | `DONE` | 3-layer system, 20 tests |
| 6 | Production Hardening — Notifications, Docker Compose, CI, tests, cold-start scripts | `DONE` | Celery beat, Resend email, GH Actions |
| 7 | Adaptation & Performance UI — REST endpoints + frontend panels for parameter drift, meta-review, equity curve | `DONE` | Insights tab with Performance + Adaptation panels |

Update the `Status` column as phases complete: `TODO` → `IN PROGRESS` → `DONE`.

---

## Project Structure (actual)

```
signal-terminal/
├── CLAUDE.md                    ← you are here
├── SIGNAL-TERMINAL-SPEC-ORIGINAL.md  ← original spec (archived)
├── docker-compose.yml
├── .env.example
├── .gitignore
├── Makefile
├── frontend/                    ← React + TypeScript
│   └── src/
│       ├── types/               ← market.ts, positions.ts, discovery.ts, adaptation.ts
│       ├── services/            ← api.ts, websocket.ts
│       ├── hooks/               ← useSignals, useRegime, usePositions, useWebSocket
│       ├── test/                ← setup.ts (Vitest + testing-library)
│       └── components/
│           ├── layout/          ← Header, Watchlist, DetailPanel
│           ├── common/          ← SignalBadge, RegimeBadge, StatBox, PnlBadge
│           ├── positions/       ← PositionsPanel, PositionList, TradeEntryForm,
│           │                      ClosePositionModal, EditPositionModal,
│           │                      PositionRow, TradeHistory
│           ├── alerts/          ← AlertFeed, AlertItem
│           ├── discovery/       ← DiscoveryPanel, ScreenerTable, WatchlistGrid,
│           │                       WatchlistCard, ScoreBar
│           └── insights/        ← InsightsPanel, AdaptationPanel, PerformancePanel,
│                                   CurrentParameters, MetaReviewCard,
│                                   ParameterDriftChart, EquityCurve,
│                                   DailyPerfTable, PerformanceSummaryStats
└── backend/
    ├── alembic.ini
    ├── requirements.txt
    └── app/
        ├── main.py              ← FastAPI entry point
        ├── config.py            ← Pydantic Settings (single source of truth)
        ├── models/              ← SQLAlchemy ORM models
        │   ├── signal.py, parameter_snapshot.py, regime_log.py
        │   ├── meta_review.py, performance.py
        │   ├── stock_universe.py, screener_result.py, watchlist.py
        │   └── position.py, exit_signal.py
        ├── schemas/             ← Pydantic request/response schemas
        │   ├── signals.py, config.py, regime.py, performance.py
        │   ├── discovery.py, positions.py
        ├── api/                 ← FastAPI route handlers
        │   ├── signals.py, regime.py, discovery.py
        │   └── positions.py, websocket.py
        ├── engine/              ← Signal engine + data providers
        │   ├── indicators.py    ← EMA, RSI, MACD, ATR, Bollinger, Stochastic, ADX, divergence
        │   ├── analyzer.py      ← Cluster-based scoring + BUY filters (R:R, 200d SMA,
        │   │                      Minervini trend template) + position sizing (Van Tharp)
        │   ├── signal_service.py ← Signal persistence + dedup (one per symbol/day)
        │   ├── data_provider.py ← DataProvider ABC (strategy pattern)
        │   ├── hybrid_provider.py ← Routes US→Massive, .TO→yfinance
        │   ├── massive_provider.py ← Massive.com OHLCV data (US stocks)
        │   ├── yfinance_provider.py ← Yahoo Finance data (TSX .TO stocks)
        │   ├── finnhub_provider.py ← Finnhub candle data (legacy)
        │   ├── massive_sentiment.py ← Massive news API + built-in sentiment (US)
        │   ├── sentiment_analyzer.py ← Finnhub news + Claude Haiku scoring (.TO)
        │   ├── fundamental_analyzer.py ← Finnhub P/E, ROE, margins, analyst recs
        │   ├── regime.py        ← Heuristic regime detector (SPY-based)
        │   ├── sentiment.py     ← (legacy) Simulated sentiment — unused
        │   ├── fundamentals.py  ← (legacy) Simulated fundamentals — unused
        │   └── live_scanner.py  ← Background loop: position checks (30min) + signal scans (60min)
        ├── discovery/           ← Stock discovery
        │   ├── universe.py      ← Seed ~4,700 stocks (Finnhub US + Wikipedia TSX 60)
        │   ├── screener.py      ← 6-dimension pre-market screener (7 indicators)
        │   └── ai_watchlist.py  ← Claude picks 20 from top 30
        ├── positions/           ← Position manager + exit strategies
        │   ├── manager.py, monitor.py
        │   └── exit_strategies/ ← base, stop_loss, trailing_stop, profit_target,
        │                           indicator_reversal, sentiment_shift,
        │                           time_based, composite
        ├── adaptation/          ← Layer 1/2/3 adaptive system
        │   ├── layer1_optimizer/  ← Bayesian optimizer (OnlineOptimizer)
        │   ├── layer2_regime/     ← HMM regime detector (5 presets)
        │   ├── layer3_meta/       ← Claude meta-analyst
        │   └── coordinator.py
        ├── services/            ← External integrations (notifications)
        ├── tasks/               ← Celery tasks + beat schedule
        └── db/
            ├── database.py      ← Async engine + session + get_db dependency
            └── migrations/
                └── versions/    ← 001_initial_schema, 002_discovery_tables,
                                    003_position_tables, 004_screener_updated_at,
                                    005_rename_max_hold_bars_to_days,
                                    006_add_effective_stop, 007_add_passes_trend_template
```

---

## Key Conventions

### Backend
- All DB operations are **async** (SQLAlchemy async session)
- Use `async def` throughout; Celery tasks wrap with `asyncio.run()`
- Pydantic v2 for schemas
- One file per domain in `api/`, `models/`, `schemas/`
- Exit strategies follow the `ExitStrategy` ABC (`positions/exit_strategies/base.py`)
- All exit strategy `evaluate()` methods return `ExitSignalResult | None`

### Frontend (Strict TypeScript)
- `strict: true` in `tsconfig.json`
- **No `any`** — use `unknown` + type guards or proper generics
- Prefer `interface` for object shapes, `type` for unions/intersections/aliases
- All props explicitly typed — no inline anonymous types
- Types defined in `src/types/` (one file per domain)
- `as` type assertions only when unavoidable (e.g., API responses) — prefer narrowing
- API calls go through `src/services/api.ts` only
- WebSocket handled in `src/services/websocket.ts`
- Tailwind for styling; dark terminal theme

### Testing
- **Unit tests required** for all critical logic before moving to next phase
- Backend tests: `backend/tests/` — 6 files, 135 tests (`pytest` + `pytest-asyncio`)
- Frontend tests: `frontend/src/` — 3 files, 30 tests (`vitest` + `@testing-library/react`)
- Critical = anything that produces numbers users act on: indicators, analyzer, exit strategies, P&L calculations, position manager, sentiment scoring
- Mock external dependencies (DB, APIs) — test pure logic
- Run backend: `cd backend && pytest tests/ -v`
- Run frontend: `cd frontend && npm test`

### Market Data Routing
| Data | US Stocks | .TO Stocks |
|---|---|---|
| OHLCV (daily + intraday) | Massive.com (unlimited) | yfinance (free) |
| News sentiment | Massive `/v2/reference/news` (built-in insights) | Finnhub `/company-news` + Claude Haiku |
| Fundamentals (P/E, ROE) | Finnhub `/stock/metric` + `/stock/recommendation` | Finnhub (same) |

### Signal Quality Filters (BUY signals must pass ALL)
1. **Conviction ≥ min_signal_strength** (regime-tuned, default 1.5)
2. **Risk/Reward ≥ 1.5:1** (potential reward ÷ potential loss)
3. **200-day SMA filter** — price must be above 200d SMA (exception: ADX < 20 range-bound)
4. **Minervini trend template** — price > 50d & 150d SMA, MAs stacked, within 25% of 52w high, 20%+ above 52w low
5. **Cluster-based scoring** — RSI/Stochastic decorrelated, ADX additive (not multiplicative), volume is the only multiplier

### Position Sizing (Van Tharp + AQR conviction overlay)
Every BUY signal includes a `position_sizing` block with calculated shares:
- Base: `risk_dollars / (entry - stop)` where `risk_dollars = portfolio × risk_per_trade_pct`
- Conviction overlay: ±25% based on signal strength
- Capped at `max_position_pct` of portfolio (default 25%)

### General
- No direct brokerage integration — user logs trades manually
- Market timezone: `America/New_York`

---

## Environment Variables (key ones)

```env
DATABASE_URL=postgresql+asyncpg://signal:signal@localhost:5555/signal_terminal
DATABASE_URL_SYNC=postgresql://signal:signal@localhost:5555/signal_terminal
REDIS_URL=redis://localhost:6380/0
ANTHROPIC_API_KEY=         # Required for Claude watchlist + meta-review + .TO sentiment
MASSIVE_API_KEY=           # Required for US market data + news sentiment
FINNHUB_API_KEY=           # Required for fundamentals + .TO news sentiment
TIMEZONE=America/New_York
TRADING_MODE=swing         # "swing" or "day"
SCREENER_UNIVERSES=sp500,nasdaq100,tsx
WATCHLIST_SIZE=20
DEFAULT_STOP_LOSS_PCT=5.0
DEFAULT_PROFIT_TARGET_PCT=10.0
DEFAULT_ATR_MULTIPLIER_STOP=2.5
DEFAULT_ATR_MULTIPLIER_TARGET=4.0
EOD_EXIT_ENABLED=false
MAX_HOLD_DAYS=25

# Position Sizing (Van Tharp fixed fractional risk)
PORTFOLIO_SIZE_CAD=10000
RISK_PER_TRADE_PCT=1.0
MAX_POSITION_PCT=25.0
```

---

## Daily Pipeline (runtime reference)

```
5:00 AM   Morning screener (~4,600 stocks, using previous close data)
10:00 AM  Morning position check
1:00 PM   Midday position check
4:15 PM   Afternoon position check
5:00 PM   Post-close screener (finalized daily bars)
5:00 PM   Regime detection (daily)
5:30 PM   Claude builds watchlist (20 picks) + email
5:45 PM   Claude daily meta-review + email
6:00 PM   Performance calculation
```

---

## Validation Checklist Per Phase

**Phase 1 — DONE:**
- [x] `GET /api/signals` returns simulated BUY/SELL signals with conviction scores
- [x] `GET /api/regime` returns a current regime state
- [x] DB migrations run cleanly (`alembic upgrade head`)
- [x] Backend starts with `uvicorn app.main:app --reload`

**Phase 2 — DONE:**
- [x] React app loads at `localhost:5173`
- [x] Watchlist sidebar renders signal list
- [x] Clicking a stock shows chart + technical/sentiment tabs
- [x] WebSocket live-updates signal feed (`signal_update` messages pushed every 5 min via live_scanner)

**Phase 3 — DONE:**
- [x] `POST /api/discovery/scan` triggers screener, top 30 results in DB
- [x] `POST /api/discovery/watchlist` calls Claude API (or fallback), 12 picks with reasoning in DB
- [x] `POST /api/discovery/seed` seeds ~830 stocks (S&P 500, NASDAQ 100, TSX)
- [x] Discovery tab in frontend — ScreenerTable (6-dimension score bars) + WatchlistGrid (AI picks with reasoning)

**Phase 4 — DONE:**
- [x] Trade entry form opens a position (TradeEntryForm → POST /api/positions)
- [x] Position monitor fires exit alerts (6 strategies: stop/trailing/target/reversal/sentiment/time)
- [x] Alerts appear in WebSocket feed in UI (AlertFeed + useWebSocket, auto-switches tab on CRITICAL)
- [x] Closing a position records outcome (ClosePositionModal → PUT /api/positions/{id}/close)

**Phase 5 — DONE:**
- [x] Layer 1 updates parameters after each closed trade (OnlineOptimizer)
- [x] Layer 2 detects and logs regime changes (AdaptiveRegimeDetector + 5 presets)
- [x] Layer 3 meta-review produces readable report (MetaAnalyst + Claude API fallback)

**Phase 6 — DONE:**
- [x] Celery beat schedule runs full daily pipeline
- [x] Resend email notifications (watchlist, meta-review, critical alerts)
- [x] Docker Compose with all services (db, redis, backend, frontend, celery worker + beat)
- [x] 165 tests across 10 files (135 backend: indicators, analyzer, exit strategies, position manager, adaptation, signal quality; 30 frontend: api, PnlBadge, SignalBadge)
- [x] Cold-start scripts (`seed_universe.py`, `seed_historical.py`)

**Phase 7 — DONE:**
- [x] `GET /api/adaptation/parameters` — current optimised parameter values
- [x] `GET /api/adaptation/log` — parameter snapshot history (limit, most recent first)
- [x] `GET /api/adaptation/reviews` — meta-review history
- [x] `GET /api/adaptation/reviews/latest` — most recent meta-review
- [x] `POST /api/adaptation/review` — manually trigger Layer 3 Claude meta-review
- [x] `GET /api/performance/daily` — daily performance history (days param)
- [x] `GET /api/performance/daily/today` — today's performance record
- [x] `GET /api/performance/summary` — aggregate win rate, cumulative return, best/worst day
- [x] AdaptationPanel frontend — current parameters, parameter drift chart, meta-review history (collapsible cards)
- [x] PerformancePanel frontend — equity curve, summary stats, daily table, 7/30/90d window picker
- [x] WebSocket live signal push — live_scanner.py broadcasts signals (5 min) + position alerts (30 s)

---

## Known Gaps / Future Work

| Item | Notes |
|---|---|
| Symbol validation in trade form | TradeEntryForm doesn't verify symbol exists in universe before submitting |
| Massive financials for US | Currently only Finnhub for fundamentals; Massive may have financials endpoint on higher plan |
| Frontend tests | 30 tests (API service, PnlBadge, SignalBadge); no component integration tests yet |

---

## Quick Start (new machine)

```powershell
# 1. Clone and enter project
git clone https://github.com/CaveDweller92/signal-terminal.git
cd signal-terminal

# 2. Copy env file
cp .env.example .env    # Edit with your API keys if needed

# 3. Start DB + Redis
docker compose up db redis -d

# 4. Install Python deps (if running backend locally)
cd backend
pip install -r requirements.txt

# 5. Run migrations + seed data
python -m alembic upgrade head
python scripts/seed_universe.py
python scripts/seed_historical.py

# 6. Start backend
uvicorn app.main:app --reload --port 8000

# 7. Start frontend (separate terminal)
cd ../frontend
npm install
npm run dev
```

Or use Docker for everything: `.\run.ps1 dev`

---

## Useful Commands

**Windows (PowerShell) — use `.\run.ps1`:**
```powershell
.\run.ps1 dev             # Start everything via Docker Compose
.\run.ps1 cold-start      # migrate + seed-universe + seed (first time)
.\run.ps1 test            # Run all backend tests
.\run.ps1 migrate         # Run Alembic migrations
.\run.ps1 seed-universe   # Load S&P 500, NASDAQ 100, TSX stocks
.\run.ps1 seed            # Generate simulated historical data
.\run.ps1 scan            # Manually trigger pre-market screener
.\run.ps1 watchlist       # Manually trigger Claude watchlist build
.\run.ps1 review          # Trigger daily meta-review
.\run.ps1 logs            # Tail backend + Celery logs
.\run.ps1                 # Show all available commands
```

**Linux/Mac — use `make`:**
```bash
make dev              # Start everything via Docker Compose
make cold-start       # migrate + seed-universe + seed
make test             # Run all backend tests
make scan             # Manually trigger pre-market screener
make watchlist        # Manually trigger Claude watchlist build
```

---

## Service URLs (when running)

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| PostgreSQL | localhost:5555 |
| Redis | localhost:6380 |
