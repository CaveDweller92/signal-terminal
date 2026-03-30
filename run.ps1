param(
    [Parameter(Position=0)]
    [string]$Command
)

$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot

$VENV = "backend\.venv"
$PYTHON = "$VENV\Scripts\python.exe"
$PIP = "$VENV\Scripts\pip.exe"

function RequireVenv {
    if (-not (Test-Path $PYTHON)) {
        Write-Host "No venv found - run .\run.ps1 install first" -ForegroundColor Cyan
        Pop-Location
        exit 1
    }
}

switch ($Command) {
    "dev"           { docker compose up --build }
    "up"            { docker compose up -d }
    "down"          { docker compose down }
    "logs"          { docker compose logs -f backend celery-worker }
    "reset-db" {
        Write-Host "=== Resetting database (drops volume + recreates) ===" -ForegroundColor Cyan
        docker compose down -v
        docker compose up db redis -d
        Write-Host "Waiting for PostgreSQL to be ready..."
        Start-Sleep -Seconds 5
        RequireVenv
        Push-Location backend; & "..\$PYTHON" -m alembic upgrade head; Pop-Location
        Write-Host "=== Database reset complete ===" -ForegroundColor Green
    }
    "docker-clean" {
        Write-Host "This will remove all Signal Terminal containers, images, and volumes." -ForegroundColor Yellow
        $confirm = Read-Host "Are you sure? (y/N)"
        if ($confirm -match "^[Yy]$") {
            docker compose down -v --rmi all
            Write-Host "=== Signal Terminal Docker resources cleaned ===" -ForegroundColor Green
        } else {
            Write-Host "Cancelled."
        }
    }
    "install" {
        if (-not (Test-Path $PYTHON)) {
            Write-Host "=== Creating virtual environment ===" -ForegroundColor Cyan
            python -m venv $VENV
        }
        Write-Host "=== Installing dependencies ===" -ForegroundColor Cyan
        & $PIP install -r backend\requirements.txt
        Write-Host "=== Install complete ===" -ForegroundColor Green
    }
    "migrate" {
        RequireVenv
        Push-Location backend; & "..\$PYTHON" -m alembic upgrade head; Pop-Location
    }
    "test" {
        RequireVenv
        Push-Location backend; & "..\$PYTHON" -m pytest tests/ -v; Pop-Location
    }
    "test-cov" {
        RequireVenv
        Push-Location backend; & "..\$PYTHON" -m pytest tests/ -v --cov=app --cov-report=term-missing; Pop-Location
    }
    "seed-universe" {
        RequireVenv
        Push-Location backend; & "..\$PYTHON" scripts/seed_universe.py; Pop-Location
    }
    "cold-start" {
        RequireVenv
        Write-Host "=== Starting database + Redis ===" -ForegroundColor Cyan
        docker compose up db redis -d
        Write-Host "Waiting for PostgreSQL to be ready..."
        Start-Sleep -Seconds 5
        Write-Host "=== Running migrations ===" -ForegroundColor Cyan
        Push-Location backend; & "..\$PYTHON" -m alembic upgrade head; Pop-Location
        Write-Host "=== Seeding universe ===" -ForegroundColor Cyan
        Push-Location backend; & "..\$PYTHON" scripts/seed_universe.py; Pop-Location
        Write-Host "=== Cold start complete ===" -ForegroundColor Green
        Write-Host "Tip: real signals will populate once the market opens and the live scanner runs."
    }
    "scan" {
        RequireVenv
        Push-Location backend; & "..\$PYTHON" -c "from app.tasks.premarket_scan import run_scan; run_scan()"; Pop-Location
    }
    "watchlist" {
        RequireVenv
        Push-Location backend; & "..\$PYTHON" -c "from app.tasks.watchlist_build import build_daily_watchlist; build_daily_watchlist()"; Pop-Location
    }
    "review" {
        RequireVenv
        Push-Location backend; & "..\$PYTHON" -c "from app.tasks.daily_meta_review import run_daily_meta_review; run_daily_meta_review()"; Pop-Location
    }
    default {
        Write-Host "Signal Terminal - Available commands:" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "  Docker:" -ForegroundColor Yellow
        Write-Host "    .\run.ps1 dev             # Start everything via Docker Compose"
        Write-Host "    .\run.ps1 up              # Start in background"
        Write-Host "    .\run.ps1 down            # Stop all containers"
        Write-Host "    .\run.ps1 logs            # Tail backend + celery logs"
        Write-Host "    .\run.ps1 reset-db        # Drop + recreate database (fresh slate)"
        Write-Host "    .\run.ps1 docker-clean    # Remove ALL Docker containers, images, volumes"
        Write-Host ""
        Write-Host "  Setup:" -ForegroundColor Yellow
        Write-Host "    .\run.ps1 install         # Create venv + pip install dependencies"
        Write-Host ""
        Write-Host "  Database:" -ForegroundColor Yellow
        Write-Host "    .\run.ps1 migrate         # Run Alembic migrations"
        Write-Host ""
        Write-Host "  Testing:" -ForegroundColor Yellow
        Write-Host "    .\run.ps1 test            # Run all tests"
        Write-Host "    .\run.ps1 test-cov        # Run tests with coverage"
        Write-Host ""
        Write-Host "  Cold Start:" -ForegroundColor Yellow
        Write-Host "    .\run.ps1 cold-start      # migrate + seed-universe"
        Write-Host "    .\run.ps1 seed-universe   # Load stock universe from Finnhub"
        Write-Host ""
        Write-Host "  Manual Triggers:" -ForegroundColor Yellow
        Write-Host "    .\run.ps1 scan            # Trigger pre-market screener"
        Write-Host "    .\run.ps1 watchlist       # Trigger AI watchlist build"
        Write-Host "    .\run.ps1 review          # Trigger daily meta-review"
    }
}

Pop-Location
