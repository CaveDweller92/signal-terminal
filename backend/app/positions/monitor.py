"""
Position Monitor — continuously checks all open positions against exit strategies.

Runs every 30 seconds during market hours (via Celery beat or manual call).
For each open position:
1. Fetch latest price data
2. Update tracking fields (current_price, P&L, high/low, bars_held)
3. Run all exit strategies via CompositeExitStrategy
4. Save triggered exit signals to DB
5. Return alerts for WebSocket broadcast
"""

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.data_provider import DataProvider
from app.models.exit_signal import ExitSignal
from app.models.position import Position
from app.positions.exit_strategies import (
    CompositeExitStrategy,
    ExitSignalResult,
    ExitUrgency,
    IndicatorReversalStrategy,
    ProfitTargetStrategy,
    SentimentShiftStrategy,
    StopLossStrategy,
    TimeBasedExitStrategy,
    TrailingStopStrategy,
)
from app.positions.manager import PositionManager

logger = logging.getLogger(__name__)


class PositionMonitor:
    def __init__(self, db: AsyncSession, data_provider: DataProvider):
        self.db = db
        self.data = data_provider
        self.manager = PositionManager(db, data_provider)

        # Build the composite exit engine with all 6 strategies
        self.exit_engine = CompositeExitStrategy(
            strategies=[
                StopLossStrategy(),
                TrailingStopStrategy(trail_atr_multiplier=2.0, activation_pct=1.5),
                ProfitTargetStrategy(),
                IndicatorReversalStrategy(),
                SentimentShiftStrategy(),
                TimeBasedExitStrategy(),
            ],
            cooldown_minutes=1440,  # 24 hours — swing trading
        )

    async def check_all_positions(self) -> list[dict]:
        """
        Main monitoring loop. Returns list of alert dicts for WebSocket broadcast.
        """
        open_positions = await self.manager.get_open_positions()
        all_alerts: list[dict] = []

        for position in open_positions:
            try:
                alerts = await self._check_position(position)
                all_alerts.extend(alerts)
            except Exception as e:
                logger.error(f"Monitor error for position {position.id} ({position.symbol}): {e}")

        return all_alerts

    async def _check_position(self, position: Position) -> list[dict]:
        """Check one position against exit strategies.

        Uses intraday bars for price/stop/target checks (catches intraday breaches),
        with daily bars for indicator-based strategies (EMA, RSI, MACD).
        """
        # Intraday bars for current price + stop/target evaluation
        intraday = await self.data.get_intraday(position.symbol)
        daily = await self.data.get_daily(position.symbol)

        if not daily:
            return []

        # Use latest intraday bar if available, else fall back to daily
        if intraday:
            current_bar = intraday[-1]
        else:
            current_bar = daily[-1]

        price = current_bar["close"]

        # Update position tracking fields
        is_long = position.direction == "LONG"
        if is_long:
            pnl_pct = (price - position.entry_price) / position.entry_price * 100
        else:
            pnl_pct = (position.entry_price - price) / position.entry_price * 100

        position.current_price = price
        # Dollar P&L = price difference × quantity
        if is_long:
            pnl_dollar = (price - position.entry_price) * position.quantity
        else:
            pnl_dollar = (position.entry_price - price) * position.quantity
        position.unrealized_pnl = round(pnl_dollar, 2)
        position.unrealized_pnl_pct = round(pnl_pct, 4)
        position.high_since_entry = max(position.high_since_entry or price, price)
        position.low_since_entry = min(position.low_since_entry or price, price)
        # Count trading days held (not monitoring cycles)
        days_held = (datetime.utcnow() - position.entry_time).days if position.entry_time else 0
        position.bars_held = max(days_held, 1)
        position.last_updated = datetime.utcnow()

        # Run exit strategies — current_bar has intraday price, daily bars for indicators
        exit_signals = await self.exit_engine.evaluate_all(position, current_bar, daily)

        # Save and build alerts
        alerts: list[dict] = []
        for signal in exit_signals:
            # Save to DB
            exit_record = ExitSignal(
                position_id=position.id,
                symbol=position.symbol,
                exit_type=signal.exit_type,
                urgency=signal.urgency.value,
                trigger_price=signal.trigger_price,
                current_price=signal.current_price,
                message=signal.message,
                details=signal.details,
            )
            self.db.add(exit_record)

            # Build alert dict for WebSocket
            alerts.append({
                "type": "exit_alert",
                "position_id": position.id,
                "symbol": position.symbol,
                "urgency": signal.urgency.value,
                "exit_type": signal.exit_type,
                "message": signal.message,
                "current_price": signal.current_price,
                "trigger_price": signal.trigger_price,
                "timestamp": datetime.utcnow().isoformat(),
            })

        await self.db.flush()
        return alerts
