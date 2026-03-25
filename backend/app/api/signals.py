"""
Signal API routes.

GET /api/signals           — analyze a list of symbols, return signals
GET /api/signals/{symbol}  — analyze a single symbol
"""

from fastapi import APIRouter, Query

from app.engine.analyzer import SignalAnalyzer
from app.engine.data_provider import get_data_provider

router = APIRouter(prefix="/api/signals", tags=["signals"])

# Default watchlist for Phase 1 (simulated — no screener yet)
DEFAULT_SYMBOLS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META",
    "TSLA", "AMD", "NFLX", "JPM", "V", "HD",
]


@router.get("")
async def get_signals(
    symbols: str | None = Query(
        None,
        description="Comma-separated symbols. Defaults to built-in watchlist.",
    ),
):
    """
    Analyze multiple symbols and return their signals.

    Returns a list of signal objects sorted by absolute conviction
    (strongest signals first).
    """
    symbol_list = (
        [s.strip().upper() for s in symbols.split(",") if s.strip()]
        if symbols
        else DEFAULT_SYMBOLS
    )

    provider = get_data_provider()
    analyzer = SignalAnalyzer(provider)

    results = []
    for symbol in symbol_list:
        signal = await analyzer.analyze(symbol)
        results.append(signal)

    # Sort by absolute conviction descending (strongest signals first)
    results.sort(key=lambda s: abs(s["conviction"]), reverse=True)

    return {"signals": results, "count": len(results)}


@router.get("/{symbol}")
async def get_signal(symbol: str):
    """Analyze a single symbol."""
    provider = get_data_provider()
    analyzer = SignalAnalyzer(provider)
    signal = await analyzer.analyze(symbol.upper())
    return signal
