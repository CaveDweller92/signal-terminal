"""Daily performance calculation — runs at 4:30 PM ET weekdays."""

import asyncio
import logging
from datetime import date

from app.tasks.celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(name="app.tasks.performance_calc.calc_daily_performance")
def calc_daily_performance():
    asyncio.run(_calc())


async def _calc():
    from sqlalchemy import select, func, delete
    from app.db.database import async_session
    from app.models.signal import Signal
    from app.models.position import Position
    from app.models.regime_log import RegimeLog
    from app.models.performance import DailyPerformance

    today = date.today()

    async with async_session() as db:
        # Clear existing for today (idempotent)
        await db.execute(
            delete(DailyPerformance).where(DailyPerformance.perf_date == today)
        )

        # Signals today
        sig_result = await db.execute(
            select(Signal.signal_type, func.count(Signal.id))
            .where(func.date(Signal.created_at) == today)
            .group_by(Signal.signal_type)
        )
        signal_counts = {row[0]: row[1] for row in sig_result.all()}

        # Trades closed today
        trades_result = await db.execute(
            select(Position)
            .where(Position.status == "CLOSED")
            .where(func.date(Position.exit_time) == today)
        )
        trades = list(trades_result.scalars().all())

        winners = [t for t in trades if (t.realized_pnl_pct or 0) > 0]
        losers = [t for t in trades if (t.realized_pnl_pct or 0) <= 0]
        returns = [t.realized_pnl_pct or 0 for t in trades]

        # Current regime
        regime_result = await db.execute(
            select(RegimeLog).order_by(RegimeLog.created_at.desc()).limit(1)
        )
        regime_log = regime_result.scalar_one_or_none()

        perf = DailyPerformance(
            perf_date=today,
            total_signals=sum(signal_counts.values()),
            buy_signals=signal_counts.get("BUY", 0),
            sell_signals=signal_counts.get("SELL", 0),
            signals_correct=len(winners),
            signals_incorrect=len(losers),
            win_rate=round(len(winners) / len(trades) * 100, 1) if trades else None,
            avg_return_pct=round(sum(returns) / len(returns), 2) if returns else None,
            best_return_pct=round(max(returns), 2) if returns else None,
            worst_return_pct=round(min(returns), 2) if returns else None,
            total_return_pct=round(sum(returns), 2) if returns else None,
            regime=regime_log.regime if regime_log else None,
        )
        db.add(perf)
        await db.commit()
        logger.info(f"Daily performance saved: {len(trades)} trades, win rate {perf.win_rate}%")
