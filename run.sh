#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

CYAN='\033[0;36m'
YELLOW='\033[0;33m'
GREEN='\033[0;32m'
RESET='\033[0m'

case "$1" in
  # Docker
  dev)           docker compose up --build ;;
  up)            docker compose up -d ;;
  down)          docker compose down ;;
  logs)          docker compose logs -f backend celery-worker ;;

  # Setup
  install)       cd backend && pip3 install -r requirements.txt ;;

  # Database
  migrate)       cd backend && python3 -m alembic upgrade head ;;

  # Testing
  test)          cd backend && python3 -m pytest tests/ -v ;;
  test-cov)      cd backend && python3 -m pytest tests/ -v --cov=app --cov-report=term-missing ;;

  # Cold Start
  seed-universe) cd backend && python3 scripts/seed_universe.py ;;
  seed)          cd backend && python3 scripts/seed_historical.py ;;
  cold-start)
    echo -e "${CYAN}=== Running migrations ===${RESET}"
    (cd backend && python3 -m alembic upgrade head)
    echo -e "${CYAN}=== Seeding universe ===${RESET}"
    (cd backend && python3 scripts/seed_universe.py)
    echo -e "${CYAN}=== Seeding historical data ===${RESET}"
    (cd backend && python3 scripts/seed_historical.py)
    echo -e "${GREEN}=== Cold start complete ===${RESET}"
    ;;

  # Manual Triggers
  scan)          cd backend && python3 -c "from app.tasks.premarket_scan import run_scan; run_scan()" ;;
  watchlist)     cd backend && python3 -c "from app.tasks.watchlist_build import build_daily_watchlist; build_daily_watchlist()" ;;
  review)        cd backend && python3 -c "from app.tasks.daily_meta_review import run_daily_meta_review; run_daily_meta_review()" ;;

  *)
    echo -e "${CYAN}Signal Terminal — Available commands:${RESET}"
    echo ""
    echo -e "${YELLOW}  Docker:${RESET}"
    echo "    ./run.sh dev             # Start everything via Docker Compose"
    echo "    ./run.sh up              # Start in background"
    echo "    ./run.sh down            # Stop all containers"
    echo "    ./run.sh logs            # Tail backend + celery logs"
    echo ""
    echo -e "${YELLOW}  Setup:${RESET}"
    echo "    ./run.sh install         # pip install backend dependencies"
    echo ""
    echo -e "${YELLOW}  Database:${RESET}"
    echo "    ./run.sh migrate         # Run Alembic migrations"
    echo ""
    echo -e "${YELLOW}  Testing:${RESET}"
    echo "    ./run.sh test            # Run all tests"
    echo "    ./run.sh test-cov        # Run tests with coverage"
    echo ""
    echo -e "${YELLOW}  Cold Start:${RESET}"
    echo "    ./run.sh cold-start      # migrate + seed-universe + seed"
    echo "    ./run.sh seed-universe   # Load stock universe"
    echo "    ./run.sh seed            # Generate historical signals"
    echo ""
    echo -e "${YELLOW}  Manual Triggers:${RESET}"
    echo "    ./run.sh scan            # Trigger pre-market screener"
    echo "    ./run.sh watchlist       # Trigger AI watchlist build"
    echo "    ./run.sh review          # Trigger daily meta-review"
    ;;
esac
