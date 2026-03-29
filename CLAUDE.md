# Signal Terminal — CLAUDE.md

> This file is loaded automatically into every Claude Code session.
> Keep it up to date as the project evolves.

---

## What This Is

A self-adapting intraday stock trading signals platform. The user executes trades manually on Wealthsimple; Signal Terminal provides the intelligence layer:
- Morning watchlist (Claude-curated, 12 picks from ~830 stocks)
- Intraday BUY/SELL signals with conviction scores
- Real-time EXIT alerts on open positions (stop loss, profit target, indicator reversal, sentiment shift, EOD)
- Self-tuning via 3-layer adaptive system (Bayesian optimizer + regime detection + Claude meta-review)

**Disclaimer:** Educational/informational only. Not financial advice.

Full spec: `SIGNAL-TERMINAL-ADAPTIVE.md`

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Recharts, Tailwind CSS |
| Backend | Python 3.11+, FastAPI, Uvicorn |
| ML/Stats | scikit-learn, scipy, numpy, pandas, hmmlearn |
| AI Agent | Anthropic Claude API (`claude-sonnet-4-5-20251001` or latest Sonnet) |
| Database | PostgreSQL 16 + SQLAlchemy (async) + Alembic |
| Cache | Redis |
| Task Queue | Celery + Redis (beat scheduler) |
| WebSocket | FastAPI WebSocket |
| Notifications | Resend (email), Web Push API |
| Market Data | Massive.com (US) + yfinance (TSX) + Finnhub news (simulated in Phase 1) |
| DevOps | Docker Compose, GitHub Actions |

---

## Build Phases

Build one phase at a time. Validate before moving on.

| # | Phase | Status | Notes |
|---|---|---|---|
| 1 | Core Backend — FastAPI skeleton, DB models, signal engine, simulated data provider | `DONE` | Ports: PostgreSQL 5555, Redis 6380 |
| 2 | Frontend Shell — React app, layout, Watchlist sidebar, Detail panel, wired to Phase 1 | `DONE` | Node 20+ required, WebSocket live signal feed still polling |
| 3 | Stock Discovery — Universe mgmt, pre-market screener, Claude AI watchlist builder | `DONE` | Needs ANTHROPIC_API_KEY for AI picks, fallback works without |
| 4 | Position Management — Open/close trades, exit strategy engine (5 strategies), WebSocket alerts | `DONE` | 5 exit strategies + WebSocket broadcast + full frontend UI |
| 5 | Adaptation — Layer 1 Bayesian optimizer, Layer 2 HMM regime detector, Layer 3 Claude meta-review | `DONE` | 3-layer system, 20 tests |
| 6 | Production Hardening — Notifications, Docker Compose, CI, tests, cold-start scripts | `DONE` | Celery beat, Resend email, GH Actions |
| 7 | Adaptation & Performance UI — REST endpoints + frontend panels for parameter drift, meta-review, equity curve | `TODO` | Backend models exist; need API routes + frontend components |

Update the `Status` column as phases complete: `TODO` → `IN PROGRESS` → `DONE`.

---

## Project Structure (actual)

```
signal-terminal/
├── CLAUDE.md                    ← you are here
├── SIGNAL-TERMINAL-ADAPTIVE.md  ← full spec
├── docker-compose.yml
├── .env.example
├── .gitignore
├── Makefile
├── frontend/                    ← React + TypeScript
│   └── src/
│       ├── types/               ← market.ts, positions.ts, discovery.ts
│       ├── services/            ← api.ts, websocket.ts
│       ├── hooks/               ← useSignals, useRegime, usePositions, useWebSocket
│       └── components/
│           ├── layout/          ← Header, Watchlist, DetailPanel
│           ├── common/          ← SignalBadge, RegimeBadge, StatBox, PnlBadge
│           ├── positions/       ← PositionsPanel, PositionList, TradeEntryForm,
│           │                      ClosePositionModal, PositionRow, TradeHistory
│           ├── alerts/          ← AlertFeed, AlertItem
│           └── discovery/       ← DiscoveryPanel, ScreenerTable, WatchlistGrid,
│                                   WatchlistCard, ScoreBar
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
        ├── engine/              ← Signal engine
        │   ├── indicators.py    ← EMA, RSI, MACD, ATR, volume ratio
        │   ├── analyzer.py      ← Conviction scoring → BUY/SELL/HOLD
        │   ├── data_provider.py ← Simulated + real (strategy pattern)
        │   ├── regime.py        ← Heuristic regime detector
        │   ├── sentiment.py     ← Simulated sentiment
        │   ├── fundamentals.py  ← Simulated fundamentals
        │   └── live_scanner.py  ← Background loop: position checks (30s) + signal scans (5min)
        ├── discovery/           ← Stock discovery
        │   ├── universe.py      ← Seed + query ~830 stocks
        │   ├── screener.py      ← 6-dimension pre-market screener
        │   └── ai_watchlist.py  ← Claude picks 12 from top 30
        ├── positions/           ← Position manager + exit strategies
        │   ├── manager.py, monitor.py
        │   └── exit_strategies/ ← base, stop_loss, profit_target,
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
                                    003_position_tables
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
- Tests live in `backend/tests/` — one file per module (e.g., `test_indicators.py`)
- Use `pytest` + `pytest-asyncio` for async tests
- Critical = anything that produces numbers users act on: indicators, analyzer, exit strategies, P&L calculations, position manager
- Mock external dependencies (DB, APIs) — test pure logic
- Run with `cd backend && pytest tests/ -v`

### General
- No direct brokerage integration — user logs trades manually
- Market timezone: `America/New_York`

---

## Environment Variables (key ones)

```env
DATABASE_URL=postgresql+asyncpg://signal:signal@localhost:5555/signal_terminal
REDIS_URL=redis://localhost:6380/0
ANTHROPIC_API_KEY=         # Required for Phase 3+ (Claude watchlist + meta-review)
MASSIVE_API_KEY=           # Required for real US market data
FINNHUB_API_KEY=           # Required for news sentiment
TIMEZONE=America/New_York
SCREENER_UNIVERSES=sp500,nasdaq100,tsx
WATCHLIST_SIZE=12
DEFAULT_STOP_LOSS_PCT=2.0
DEFAULT_PROFIT_TARGET_PCT=3.0
DEFAULT_ATR_MULTIPLIER_STOP=1.5
DEFAULT_ATR_MULTIPLIER_TARGET=2.5
EOD_EXIT_WARNING_MINUTES=15
MAX_HOLD_BARS=60
```

---

## Daily Pipeline (runtime reference)

```
5:00 AM   Pre-market screener (~830 stocks)
6:00 AM   Claude builds watchlist (12 picks) + email
9:30 AM   Signal engine + position monitor active
Ongoing   Entry signals on watchlist; exit alerts on open positions
Every 30m Regime detection
3:45 PM   EOD exit warnings
3:55 PM   CRITICAL EOD alerts
4:15 PM   Claude daily meta-review + email
4:30 PM   Performance calculation
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
- [x] Position monitor fires exit alerts (5 strategies: stop/target/reversal/sentiment/EOD)
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
- [x] 1,359 lines of tests across 6 files (indicators, analyzer, exit strategies, position manager, adaptation)
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
| Real market data | Massive.com (US) + yfinance (TSX) + Finnhub news + Claude sentiment — fully wired, requires API keys |
| Symbol validation in trade form | TradeEntryForm doesn't verify symbol exists in universe before submitting |
| Adaptation/Performance UI | Done — Insights tab with Performance (equity curve, daily table) + Adaptation (parameter drift, meta-reviews) |
| WebSocket signal feed | live_scanner.py broadcasts every 5 min during market hours |
| Real sentiment/fundamentals | Both return simulated data; real API integration deferred |

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
