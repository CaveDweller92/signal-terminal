from datetime import date, datetime

from pydantic import BaseModel


class DailyPerformanceResponse(BaseModel):
    id: int
    perf_date: date
    total_signals: int = 0
    buy_signals: int = 0
    sell_signals: int = 0
    signals_correct: int = 0
    signals_incorrect: int = 0
    win_rate: float | None = None
    avg_return_pct: float | None = None
    best_return_pct: float | None = None
    worst_return_pct: float | None = None
    total_return_pct: float | None = None
    regime: str | None = None
    breakdown: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PerformanceSummaryResponse(BaseModel):
    """Aggregate performance across a date range."""
    days: int
    total_signals: int
    total_correct: int
    overall_win_rate: float | None = None
    avg_daily_return_pct: float | None = None
    cumulative_return_pct: float | None = None
    best_day: DailyPerformanceResponse | None = None
    worst_day: DailyPerformanceResponse | None = None
    daily: list[DailyPerformanceResponse]
