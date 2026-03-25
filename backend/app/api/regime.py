"""
Regime API routes.

GET /api/regime          — current market regime
GET /api/regime/{symbol} — regime detection for a specific symbol/index
"""

from fastapi import APIRouter

from app.engine.data_provider import get_data_provider
from app.engine.regime import RegimeDetector

router = APIRouter(prefix="/api/regime", tags=["regime"])


@router.get("")
async def get_regime():
    """
    Detect the current market regime using SPY as a broad market proxy.

    Returns regime type, confidence, and the underlying features
    that drove the classification.
    """
    provider = get_data_provider()
    detector = RegimeDetector(provider)
    result = await detector.detect("SPY")
    return result


@router.get("/{symbol}")
async def get_regime_for_symbol(symbol: str):
    """
    Detect regime for a specific symbol or index.

    Useful for comparing individual stock behavior against
    the broad market regime.
    """
    provider = get_data_provider()
    detector = RegimeDetector(provider)
    result = await detector.detect(symbol.upper())
    return result
