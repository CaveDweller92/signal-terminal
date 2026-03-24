.PHONY: dev up down migrate test seed seed-universe backtest train-regime scan watchlist logs

dev:          docker compose up --build
up:           docker compose up -d
down:         docker compose down
migrate:      cd backend && alembic upgrade head
test:         cd backend && pytest tests/ -v
seed-universe: cd backend && python scripts/seed_universe.py
seed:         cd backend && python scripts/seed_historical.py
backtest:     cd backend && python scripts/backtest.py
train-regime: cd backend && python scripts/train_regime_model.py
scan:         cd backend && python -c "from app.tasks.premarket_scan import run_scan; run_scan()"
watchlist:    cd backend && python -c "from app.tasks.watchlist_build import build_daily_watchlist; build_daily_watchlist()"
logs:         docker compose logs -f backend celery-worker
