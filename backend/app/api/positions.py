"""
Position API routes.

POST /api/positions              — open a new position
GET  /api/positions              — list open positions
PUT  /api/positions/{id}/close   — close a position
PUT  /api/positions/{id}/exits   — update exit levels
GET  /api/positions/{id}/signals — exit signals for a position
GET  /api/positions/history      — closed trade history
GET  /api/positions/stats        — aggregate trade statistics
POST /api/positions/monitor      — manually trigger position monitor
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.engine.data_provider import get_data_provider
from app.models.exit_signal import ExitSignal
from app.positions.manager import PositionManager
from app.positions.monitor import PositionMonitor
from app.schemas.positions import (
    CloseInput,
    ExitSignalResponse,
    ExitUpdateInput,
    PositionResponse,
    TradeInput,
    TradeStatsResponse,
)

router = APIRouter(prefix="/api/positions", tags=["positions"])


def _get_manager(db: AsyncSession) -> PositionManager:
    return PositionManager(db, get_data_provider())


@router.post("", response_model=PositionResponse)
async def open_position(trade: TradeInput, db: AsyncSession = Depends(get_db)):
    """
    Open a new position. System auto-computes ATR-based stop/target
    if not provided by the user.
    """
    manager = _get_manager(db)
    position = await manager.open_position(trade.model_dump(exclude_none=True))
    return PositionResponse.model_validate(position)


@router.get("", response_model=list[PositionResponse])
async def get_open_positions(db: AsyncSession = Depends(get_db)):
    """List all currently open positions with live P&L."""
    manager = _get_manager(db)
    positions = await manager.get_open_positions()
    return [PositionResponse.model_validate(p) for p in positions]


@router.put("/{position_id}/close", response_model=PositionResponse)
async def close_position(
    position_id: int, close: CloseInput, db: AsyncSession = Depends(get_db)
):
    """Close a position and record the outcome."""
    manager = _get_manager(db)
    try:
        position = await manager.close_position(
            position_id, close.exit_price, close.exit_reason or "manual"
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return PositionResponse.model_validate(position)


@router.put("/{position_id}/exits", response_model=PositionResponse)
async def update_exit_levels(
    position_id: int, exits: ExitUpdateInput, db: AsyncSession = Depends(get_db)
):
    """Update stop loss / profit target on an open position."""
    manager = _get_manager(db)
    try:
        position = await manager.update_exit_levels(
            position_id, exits.model_dump(exclude_none=True)
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return PositionResponse.model_validate(position)


@router.get("/{position_id}/signals", response_model=list[ExitSignalResponse])
async def get_exit_signals(position_id: int, db: AsyncSession = Depends(get_db)):
    """Get all exit signals generated for a position."""
    result = await db.execute(
        select(ExitSignal)
        .where(ExitSignal.position_id == position_id)
        .order_by(ExitSignal.created_at.desc())
    )
    signals = list(result.scalars().all())
    return [ExitSignalResponse.model_validate(s) for s in signals]


@router.get("/history", response_model=list[PositionResponse])
async def get_trade_history(days: int = 30, db: AsyncSession = Depends(get_db)):
    """Get closed trade history."""
    manager = _get_manager(db)
    trades = await manager.get_trade_history(days)
    return [PositionResponse.model_validate(t) for t in trades]


@router.get("/stats", response_model=TradeStatsResponse)
async def get_trade_stats(days: int = 30, db: AsyncSession = Depends(get_db)):
    """Get aggregate trade statistics for closed trades."""
    manager = _get_manager(db)
    trades = await manager.get_trade_history(days)

    if not trades:
        return TradeStatsResponse()

    wins = [t for t in trades if (t.realized_pnl_pct or 0) > 0]
    losses = [t for t in trades if (t.realized_pnl_pct or 0) <= 0]

    total_gains = sum(t.realized_pnl_pct or 0 for t in wins)
    total_losses = abs(sum(t.realized_pnl_pct or 0 for t in losses))

    return TradeStatsResponse(
        total_trades=len(trades),
        wins=len(wins),
        losses=len(losses),
        win_rate=round(len(wins) / len(trades) * 100, 1) if trades else None,
        avg_return_pct=round(sum(t.realized_pnl_pct or 0 for t in trades) / len(trades), 2) if trades else None,
        avg_winner_pct=round(total_gains / len(wins), 2) if wins else None,
        avg_loser_pct=round(-total_losses / len(losses), 2) if losses else None,
        best_trade_pct=round(max(t.realized_pnl_pct or 0 for t in trades), 2),
        worst_trade_pct=round(min(t.realized_pnl_pct or 0 for t in trades), 2),
        profit_factor=round(total_gains / total_losses, 2) if total_losses > 0 else None,
        avg_bars_held=round(sum(t.bars_held or 0 for t in trades) / len(trades), 1),
    )


@router.post("/monitor")
async def trigger_monitor(db: AsyncSession = Depends(get_db)):
    """
    Manually trigger the position monitor.
    Returns all exit alerts generated this cycle.
    In production, this runs automatically every 30 seconds via Celery beat.
    """
    monitor = PositionMonitor(db, get_data_provider())
    alerts = await monitor.check_all_positions()
    return {"alerts": alerts, "count": len(alerts)}
