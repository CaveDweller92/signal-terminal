"""
Adaptation API routes.

GET /api/adaptation/parameters        — latest parameter snapshot (current tuned values)
GET /api/adaptation/log               — parameter snapshot history (most recent first)
GET /api/adaptation/reviews           — meta-review history (most recent first)
GET /api/adaptation/reviews/latest    — today's or most recent meta-review
POST /api/adaptation/review           — manually trigger a meta-review (Layer 3)
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.parameter_snapshot import ParameterSnapshot
from app.models.meta_review import MetaReview
from app.schemas.adaptation import ParameterSnapshotResponse, MetaReviewResponse
from app.adaptation.coordinator import on_daily_review

router = APIRouter(prefix="/api/adaptation", tags=["adaptation"])


@router.get("/parameters", response_model=ParameterSnapshotResponse)
async def get_current_parameters(db: AsyncSession = Depends(get_db)):
    """
    Return the most recent parameter snapshot — the current optimised values
    that the signal engine and exit strategies are using.
    """
    result = await db.execute(
        select(ParameterSnapshot)
        .order_by(desc(ParameterSnapshot.created_at))
        .limit(1)
    )
    snapshot = result.scalar_one_or_none()

    if snapshot is None:
        # No snapshots yet — return hard-coded defaults so the UI always has data
        from app.config import settings
        return ParameterSnapshotResponse(
            id=0,
            snapshot_type="default",
            trigger="no snapshots recorded yet",
            rsi_period=14,
            rsi_overbought=70,
            rsi_oversold=30,
            ema_fast=9,
            ema_slow=21,
            volume_multiplier=1.5,
            min_signal_strength=1.5,
            technical_weight=0.5,
            sentiment_weight=0.3,
            fundamental_weight=0.2,
            atr_stop_multiplier=settings.default_atr_multiplier_stop,
            atr_target_multiplier=settings.default_atr_multiplier_target,
            default_stop_loss_pct=settings.default_stop_loss_pct,
            default_profit_target_pct=settings.default_profit_target_pct,
            max_hold_days=settings.max_hold_days,
            full_config=None,
            created_at=__import__("datetime").datetime.utcnow(),
        )

    return ParameterSnapshotResponse.model_validate(snapshot)


@router.get("/log", response_model=list[ParameterSnapshotResponse])
async def get_parameter_log(
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """
    Return the parameter snapshot history, most recent first.
    Each entry represents a tuning event (scheduled, regime change, or manual).
    """
    result = await db.execute(
        select(ParameterSnapshot)
        .order_by(desc(ParameterSnapshot.created_at))
        .limit(limit)
    )
    snapshots = list(result.scalars().all())
    return [ParameterSnapshotResponse.model_validate(s) for s in snapshots]


@router.get("/reviews", response_model=list[MetaReviewResponse])
async def get_meta_reviews(
    limit: int = Query(default=30, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
):
    """
    Return the daily meta-review history, most recent first.
    Each entry is Claude's assessment of the previous day's performance.
    """
    result = await db.execute(
        select(MetaReview)
        .order_by(desc(MetaReview.review_date))
        .limit(limit)
    )
    reviews = list(result.scalars().all())
    return [MetaReviewResponse.model_validate(r) for r in reviews]


@router.get("/reviews/latest", response_model=MetaReviewResponse | None)
async def get_latest_review(db: AsyncSession = Depends(get_db)):
    """Return the most recent meta-review."""
    result = await db.execute(
        select(MetaReview)
        .order_by(desc(MetaReview.review_date))
        .limit(1)
    )
    review = result.scalar_one_or_none()
    if review is None:
        return None
    return MetaReviewResponse.model_validate(review)


@router.post("/review")
async def trigger_meta_review(db: AsyncSession = Depends(get_db)):
    """
    Manually trigger a Layer 3 Claude meta-review.
    Normally runs automatically at 4:15 PM ET via Celery beat.
    """
    result = await on_daily_review(db)
    return {"triggered": True, **result}
