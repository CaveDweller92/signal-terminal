#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

CYAN='\033[0;36m'
YELLOW='\033[0;33m'
GREEN='\033[0;32m'
RESET='\033[0m'

VENV="backend/.venv"
PYTHON="$VENV/bin/python"
PIP="$VENV/bin/pip"

# Ensure venv exists before running any Python command
_require_venv() {
  if [ ! -f "$PYTHON" ]; then
    echo -e "${CYAN}No venv found — run ./run.sh install first${RESET}"
    exit 1
  fi
}

case "$1" in
  # Docker
  dev)           docker compose up --build ;;
  up)            docker compose up -d ;;
  down)          docker compose down ;;
  logs)          docker compose logs -f backend celery-worker ;;
  reset-db)
    echo -e "${CYAN}=== Resetting database (drops volume + recreates) ===${RESET}"
    docker compose down -v
    docker compose up db redis -d
    echo "Waiting for PostgreSQL to be ready..."
    sleep 5
    _require_venv
    (cd backend && ../"$PYTHON" -m alembic upgrade head)
    echo -e "${GREEN}=== Database reset complete ===${RESET}"
    ;;

  # Setup — creates venv + installs deps
  install)
    if [ ! -f "$PYTHON" ]; then
      echo -e "${CYAN}=== Creating virtual environment ===${RESET}"
      python3 -m venv "$VENV"
    fi
    echo -e "${CYAN}=== Installing dependencies ===${RESET}"
    "$PIP" install -r backend/requirements.txt
    echo -e "${GREEN}=== Install complete ===${RESET}"
    ;;

  # Database
  migrate)
    _require_venv
    (cd backend && ../"$PYTHON" -m alembic upgrade head)
    ;;

  # Testing
  test)
    _require_venv
    (cd backend && ../"$PYTHON" -m pytest tests/ -v)
    ;;
  test-cov)
    _require_venv
    (cd backend && ../"$PYTHON" -m pytest tests/ -v --cov=app --cov-report=term-missing)
    ;;

  # Cold Start
  seed-universe)
    _require_venv
    (cd backend && ../"$PYTHON" scripts/seed_universe.py)
    ;;
  seed)
    _require_venv
    (cd backend && ../"$PYTHON" scripts/seed_historical.py)
    ;;
  cold-start)
    _require_venv
    echo -e "${CYAN}=== Starting database + Redis ===${RESET}"
    docker compose up db redis -d
    echo "Waiting for PostgreSQL to be ready..."
    sleep 5
    echo -e "${CYAN}=== Running migrations ===${RESET}"
    (cd backend && ../"$PYTHON" -m alembic upgrade head)
    echo -e "${CYAN}=== Seeding universe ===${RESET}"
    (cd backend && ../"$PYTHON" scripts/seed_universe.py)
    echo -e "${GREEN}=== Cold start complete ===${RESET}"
    echo "Tip: real signals will populate once the market opens and the live scanner runs."
    ;;

  # Manual Triggers
  scan)
    _require_venv
    (cd backend && ../"$PYTHON" -c "from app.tasks.premarket_scan import run_scan; run_scan()")
    ;;
  watchlist)
    _require_venv
    (cd backend && ../"$PYTHON" -c "from app.tasks.watchlist_build import build_daily_watchlist; build_daily_watchlist()")
    ;;
  review)
    _require_venv
    (cd backend && ../"$PYTHON" -c "from app.tasks.daily_meta_review import run_daily_meta_review; run_daily_meta_review()")
    ;;

  *)
    echo -e "${CYAN}Signal Terminal — Available commands:${RESET}"
    echo ""
    echo -e "${YELLOW}  Docker:${RESET}"
    echo "    ./run.sh dev             # Start everything via Docker Compose"
    echo "    ./run.sh up              # Start in background"
    echo "    ./run.sh down            # Stop all containers"
    echo "    ./run.sh logs            # Tail backend + celery logs"
    echo "    ./run.sh reset-db        # Drop + recreate database (fresh slate)"
    echo ""
    echo -e "${YELLOW}  Setup:${RESET}"
    echo "    ./run.sh install         # Create venv + pip install dependencies"
    echo ""
    echo -e "${YELLOW}  Database:${RESET}"
    echo "    ./run.sh migrate         # Run Alembic migrations"
    echo ""
    echo -e "${YELLOW}  Testing:${RESET}"
    echo "    ./run.sh test            # Run all tests"
    echo "    ./run.sh test-cov        # Run tests with coverage"
    echo ""
    echo -e "${YELLOW}  Cold Start:${RESET}"
    echo "    ./run.sh cold-start      # migrate + seed-universe (no fake signals)"
    echo "    ./run.sh seed-universe   # Load stock universe"
    echo "    ./run.sh seed            # Generate historical signals"
    echo ""
    echo -e "${YELLOW}  Manual Triggers:${RESET}"
    echo "    ./run.sh scan            # Trigger pre-market screener"
    echo "    ./run.sh watchlist       # Trigger AI watchlist build"
    echo "    ./run.sh review          # Trigger daily meta-review"
    ;;
esac
