.PHONY: dev up down migrate test seed seed-universe scan watchlist logs cold-start monitor review

# Docker
dev:          docker compose up --build
up:           docker compose up -d
down:         docker compose down
logs:         docker compose logs -f backend celery-worker

# Database
migrate:      cd backend && alembic upgrade head

# Testing
test:         cd backend && pytest tests/ -v
test-cov:     cd backend && pytest tests/ -v --cov=app --cov-report=term-missing

# Cold Start (run in order)
seed-universe: cd backend && python scripts/seed_universe.py
seed:         cd backend && python scripts/seed_historical.py
cold-start:   make migrate && make seed-universe && make seed

# Manual Triggers
scan:         cd backend && python -c "from app.tasks.premarket_scan import run_scan; run_scan()"
watchlist:    cd backend && python -c "from app.tasks.watchlist_build import build_daily_watchlist; build_daily_watchlist()"
monitor:      cd backend && python -c "import asyncio; from app.db.database import async_session; from app.engine.data_provider import get_data_provider; from app.positions.monitor import PositionMonitor; asyncio.run((lambda: PositionMonitor(async_session(), get_data_provider()).check_all_positions())())"
review:       cd backend && python -c "from app.tasks.daily_meta_review import run_daily_meta_review; run_daily_meta_review()"
