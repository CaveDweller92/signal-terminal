"""
Performance API routes.

GET /api/performance/daily            — daily performance history (most recent first)
GET /api/performance/daily/today      — today's performance record
GET /api/performance/summary          — aggregate summary across N days
"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.performance import DailyPerformance
from app.schemas.performance import DailyPerformanceResponse, PerformanceSummaryResponse

router = APIRouter(prefix="/api/performance", tags=["performance"])


@router.get("/daily", response_model=list[DailyPerformanceResponse])
async def get_daily_performance(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """
    Return daily performance records for the last N days, most recent first.
    Each record is computed by the nightly performance_calc Celery task.
    """
    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(DailyPerformance)
        .where(DailyPerformance.perf_date >= since)
        .order_by(desc(DailyPerformance.perf_date))
    )
    records = list(result.scalars().all())
    return [DailyPerformanceResponse.model_validate(r) for r in records]


@router.get("/daily/today", response_model=DailyPerformanceResponse | None)
async def get_today_performance(db: AsyncSession = Depends(get_db)):
    """Return today's performance record, or null if not yet calculated."""
    result = await db.execute(
        select(DailyPerformance).where(DailyPerformance.perf_date == date.today())
    )
    record = result.scalar_one_or_none()
    if record is None:
        return None
    return DailyPerformanceResponse.model_validate(record)


@router.get("/summary", response_model=PerformanceSummaryResponse)
async def get_performance_summary(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """
    Return an aggregate performance summary across the last N days.
    Computes overall win rate, cumulative return, and best/worst day.
    """
    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(DailyPerformance)
        .where(DailyPerformance.perf_date >= since)
        .order_by(desc(DailyPerformance.perf_date))
    )
    records = list(result.scalars().all())

    if not records:
        return PerformanceSummaryResponse(
            days=days,
            total_signals=0,
            total_correct=0,
            daily=[],
        )

    total_signals = sum(r.total_signals for r in records)
    total_correct = sum(r.signals_correct for r in records)
    overall_win_rate = (total_correct / total_signals * 100) if total_signals > 0 else None

    returns = [r.total_return_pct for r in records if r.total_return_pct is not None]
    avg_daily = sum(returns) / len(returns) if returns else None
    cumulative = sum(returns) if returns else None

    daily_responses = [DailyPerformanceResponse.model_validate(r) for r in records]

    records_with_return = [r for r in records if r.total_return_pct is not None]
    best = max(records_with_return, key=lambda r: r.total_return_pct) if records_with_return else None
    worst = min(records_with_return, key=lambda r: r.total_return_pct) if records_with_return else None

    return PerformanceSummaryResponse(
        days=days,
        total_signals=total_signals,
        total_correct=total_correct,
        overall_win_rate=round(overall_win_rate, 1) if overall_win_rate is not None else None,
        avg_daily_return_pct=round(avg_daily, 2) if avg_daily is not None else None,
        cumulative_return_pct=round(cumulative, 2) if cumulative is not None else None,
        best_day=DailyPerformanceResponse.model_validate(best) if best else None,
        worst_day=DailyPerformanceResponse.model_validate(worst) if worst else None,
        daily=daily_responses,
    )
