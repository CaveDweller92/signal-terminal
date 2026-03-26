"""
Signal Terminal — FastAPI application entry point.

Start with:
    uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.signals import router as signals_router
from app.api.regime import router as regime_router
from app.api.discovery import router as discovery_router

app = FastAPI(
    title="Signal Terminal",
    description="Self-adapting intraday stock trading signals",
    version="0.1.0",
)

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
