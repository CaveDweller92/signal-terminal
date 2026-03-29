"""
Signal Terminal — FastAPI application entry point.

Start with:
    uvicorn app.main:app --reload
"""

import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.signals import router as signals_router
from app.api.regime import router as regime_router
from app.api.discovery import router as discovery_router
from app.api.positions import router as positions_router
from app.api.websocket import router as websocket_router
from app.api.adaptation import router as adaptation_router
from app.api.performance import router as performance_router
from app.engine.live_scanner import run_live_scanner

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Signal Terminal",
    description="Self-adapting intraday stock trading signals",
    version="0.1.0",
)

_scanner_task: asyncio.Task | None = None


@app.on_event("startup")
async def startup_event():
    """Log configuration status on startup and launch background scanner."""
    global _scanner_task
    logger.info("Signal Terminal starting up...")
    logger.info(f"  Simulated data: {settings.use_simulated_data}")
    if settings.use_simulated_data or not settings.has_market_data_key:
        logger.warning("  Market data: SIMULATED (set MASSIVE_API_KEY or USE_SIMULATED_DATA=false for real data)")
    else:
        provider = "Massive" if settings.massive_api_key else "yfinance"
        logger.info(f"  Market data: {provider} (real data)")
    logger.info(f"  Anthropic API: {'configured' if settings.has_anthropic_key else 'not configured (fallback mode)'}")
    logger.info(f"  Notifications: {'configured' if settings.resend_api_key else 'not configured (logging only)'}")
    logger.info(f"  Timezone: {settings.timezone}")
    _scanner_task = asyncio.create_task(run_live_scanner())


@app.on_event("shutdown")
async def shutdown_event():
    """Cancel the background scanner on shutdown."""
    global _scanner_task
    if _scanner_task and not _scanner_task.done():
        _scanner_task.cancel()
        try:
            await _scanner_task
        except asyncio.CancelledError:
            pass

# CORS — allow the React frontend (localhost:5173) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount route groups
app.include_router(signals_router)
app.include_router(regime_router)
app.include_router(discovery_router)
app.include_router(positions_router)
app.include_router(websocket_router)
app.include_router(adaptation_router)
app.include_router(performance_router)


@app.get("/")
async def root():
    return {
        "name": "Signal Terminal",
        "version": "0.1.0",
        "status": "running",
        "simulated_data": settings.use_simulated_data,
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
