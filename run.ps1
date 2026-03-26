param(
    [Parameter(Position=0)]
    [string]$Command
)

$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot

switch ($Command) {
    # Docker
    "dev"           { docker compose up --build }
    "up"            { docker compose up -d }
    "down"          { docker compose down }
    "logs"          { docker compose logs -f backend celery-worker }

    # Database
    "migrate"       { Push-Location backend; python -m alembic upgrade head; Pop-Location }

    # Testing
    "test"          { Push-Location backend; python -m pytest tests/ -v; Pop-Location }
    "test-cov"      { Push-Location backend; python -m pytest tests/ -v --cov=app --cov-report=term-missing; Pop-Location }

    # Cold Start (run in order)
    "seed-universe" { Push-Location backend; python scripts/seed_universe.py; Pop-Location }
    "seed"          { Push-Location backend; python scripts/seed_historical.py; Pop-Location }
    "cold-start"    {
        Write-Host "=== Running migrations ===" -ForegroundColor Cyan
        Push-Location backend; python -m alembic upgrade head; Pop-Location
        Write-Host "=== Seeding universe ===" -ForegroundColor Cyan
        Push-Location backend; python scripts/seed_universe.py; Pop-Location
        Write-Host "=== Seeding historical data ===" -ForegroundColor Cyan
        Push-Location backend; python scripts/seed_historical.py; Pop-Location
        Write-Host "=== Cold start complete ===" -ForegroundColor Green
    }

    # Manual Triggers
    "scan"          { Push-Location backend; python -c "from app.tasks.premarket_scan import run_scan; run_scan()"; Pop-Location }
    "watchlist"     { Push-Location backend; python -c "from app.tasks.watchlist_build import build_daily_watchlist; build_daily_watchlist()"; Pop-Location }
    "review"        { Push-Location backend; python -c "from app.tasks.daily_meta_review import run_daily_meta_review; run_daily_meta_review()"; Pop-Location }

    default {
        Write-Host "Signal Terminal — Available commands:" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "  Docker:" -ForegroundColor Yellow
        Write-Host "    .\run.ps1 dev             # Start everything via Docker Compose"
        Write-Host "    .\run.ps1 up              # Start in background"
        Write-Host "    .\run.ps1 down            # Stop all containers"
        Write-Host "    .\run.ps1 logs            # Tail backend + celery logs"
        Write-Host ""
        Write-Host "  Database:" -ForegroundColor Yellow
        Write-Host "    .\run.ps1 migrate         # Run Alembic migrations"
        Write-Host ""
        Write-Host "  Testing:" -ForegroundColor Yellow
        Write-Host "    .\run.ps1 test            # Run all tests"
        Write-Host "    .\run.ps1 test-cov        # Run tests with coverage"
        Write-Host ""
        Write-Host "  Cold Start:" -ForegroundColor Yellow
        Write-Host "    .\run.ps1 cold-start      # migrate + seed-universe + seed"
        Write-Host "    .\run.ps1 seed-universe   # Load stock universe"
        Write-Host "    .\run.ps1 seed            # Generate historical signals"
        Write-Host ""
        Write-Host "  Manual Triggers:" -ForegroundColor Yellow
        Write-Host "    .\run.ps1 scan            # Trigger pre-market screener"
        Write-Host "    .\run.ps1 watchlist        # Trigger AI watchlist build"
        Write-Host "    .\run.ps1 review          # Trigger daily meta-review"
    }
}

Pop-Location
