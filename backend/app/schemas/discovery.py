from datetime import date, datetime

from pydantic import BaseModel


class StockUniverseResponse(BaseModel):
    id: int
    symbol: str
    name: str
    exchange: str
    universe: str
    sector: str | None = None
    industry: str | None = None
    country: str
    currency: str
    is_active: bool

    model_config = {"from_attributes": True}


class ScreenerResultResponse(BaseModel):
    id: int
    scan_date: date
    symbol: str
    exchange: str | None = None
    composite_score: float
    volume_score: float | None = None
    gap_score: float | None = None
    technical_score: float | None = None
    fundamental_score: float | None = None
    news_score: float | None = None
    sector_score: float | None = None
    premarket_gap_pct: float | None = None
    relative_volume: float | None = None
    sector: str | None = None
    has_catalyst: bool

    model_config = {"from_attributes": True}


class WatchlistEntryResponse(BaseModel):
    id: int
    watch_date: date
    symbol: str
    exchange: str | None = None
    source: str
    ai_reasoning: str | None = None
    screener_rank: int | None = None
    sector: str | None = None
    regime_at_pick: str | None = None

    model_config = {"from_attributes": True}


class ScanResponse(BaseModel):
    scan_date: date
    stocks_scanned: int
    results_saved: int
    top_results: list[ScreenerResultResponse]


class WatchlistResponse(BaseModel):
    watch_date: date
    picks: list[WatchlistEntryResponse]
    source: str
