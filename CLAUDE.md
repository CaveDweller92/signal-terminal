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
| Market Data | Polygon.io or Finnhub (simulated in Phase 1) |
| DevOps | Docker Compose, GitHub Actions |

---

## Build Phases

Build one phase at a time. Validate before moving on.

| # | Phase | Status | Notes |
|---|---|---|---|
| 1 | Core Backend — FastAPI skeleton, DB models, signal engine, simulated data provider | `TODO` | Start here |
| 2 | Frontend Shell — React app, layout, Watchlist sidebar, Detail panel, wired to Phase 1 | `TODO` | |
| 3 | Stock Discovery — Universe mgmt, pre-market screener, Claude AI watchlist builder | `TODO` | Needs ANTHROPIC_API_KEY |
| 4 | Position Management — Open/close trades, exit strategy engine (5 strategies), WebSocket alerts | `TODO` | Core new feature |
| 5 | Adaptation — Layer 1 Bayesian optimizer, Layer 2 HMM regime detector, Layer 3 Claude meta-review | `TODO` | Most complex |
| 6 | Production Hardening — Notifications, Docker Compose, CI, tests, cold-start scripts | `TODO` | |

Update the `Status` column as phases complete: `TODO` → `IN PROGRESS` → `DONE`.

---

## Project Structure (target)

```
signal-terminal/
├── CLAUDE.md                    ← you are here
├── SIGNAL-TERMINAL-ADAPTIVE.md  ← full spec
├── docker-compose.yml
├── .env.example
├── Makefile
├── frontend/                    ← React + TypeScript
└── backend/                     ← Python + FastAPI
    └── app/
        ├── main.py
        ├── config.py
        ├── models/              ← SQLAlchemy ORM models
        ├── schemas/             ← Pydantic request/response schemas
        ├── api/                 ← FastAPI route handlers
        ├── engine/              ← Signal engine (indicators, analyzer, data provider)
        ├── positions/           ← Position manager + exit strategies
        ├── discovery/           ← Universe, screener, AI watchlist
        ├── adaptation/          ← Layer 1/2/3 adaptive system
        ├── services/            ← External integrations (market data, news, Claude API)
        ├── tasks/               ← Celery tasks + beat schedule
        └── db/                  ← Database init + migrations
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

### General
- No direct brokerage integration — user logs trades manually
- `USE_SIMULATED_DATA=true` in Phase 1; real API keys added later
- Market timezone: `America/New_York`

---

## Environment Variables (key ones)

```env
DATABASE_URL=postgresql+asyncpg://signal:signal@localhost:5432/signal_terminal
REDIS_URL=redis://localhost:6379/0
ANTHROPIC_API_KEY=         # Required for Phase 3+ (Claude watchlist + meta-review)
POLYGON_API_KEY=           # Optional — simulated data used if blank
FINNHUB_API_KEY=           # Optional
USE_SIMULATED_DATA=true
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

**Phase 1 done when:**
- [ ] `GET /api/signals` returns simulated BUY/SELL signals with conviction scores
- [ ] `GET /api/regime` returns a current regime state
- [ ] DB migrations run cleanly (`alembic upgrade head`)
- [ ] Backend starts with `uvicorn app.main:app --reload`

**Phase 2 done when:**
- [ ] React app loads at `localhost:5173`
- [ ] Watchlist sidebar renders signal list
- [ ] Clicking a stock shows chart + technical/sentiment tabs
- [ ] WebSocket live-updates signal feed

**Phase 3 done when:**
- [ ] `make scan` triggers screener, top 30 results in DB
- [ ] `make watchlist` calls Claude API, 12 picks with reasoning in DB
- [ ] Discovery tab shows screener heatmap + AI picks

**Phase 4 done when:**
- [ ] Trade entry form opens a position
- [ ] Position monitor fires exit alerts (stop/target/reversal/sentiment/EOD)
- [ ] Alerts appear in WebSocket feed in UI
- [ ] Closing a position records outcome

**Phase 5 done when:**
- [ ] Layer 1 updates parameters after each closed trade
- [ ] Layer 2 detects and logs regime changes
- [ ] Layer 3 meta-review runs at 4:15 PM and produces a readable report

---

## Useful Commands

```bash
make dev              # Start everything via Docker Compose
make migrate          # Run Alembic migrations
make seed-universe    # Load S&P 500, NASDAQ 100, TSX stocks
make seed             # Generate simulated historical data
make train-regime     # Train HMM regime model on historical data
make backtest         # Backtest strategy
make scan             # Manually trigger pre-market screener
make watchlist        # Manually trigger Claude watchlist build
make test             # Run backend tests
make logs             # Tail backend + Celery logs
```
