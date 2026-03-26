"""
Position Manager — lifecycle orchestrator for trading positions.

Flow:
1. User opens position (manual entry via API)
2. System attaches exit strategy config (ATR-based stops/targets)
3. Position monitor continuously evaluates exit conditions
4. User closes position (manual via API)
5. Outcome recorded → feeds into optimizer (Phase 5)
"""

from datetime import datetime

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.engine.data_provider import DataProvider
from app.engine.regime import RegimeDetector
from app.models.position import Position


class PositionManager:
    def __init__(self, db: AsyncSession, data_provider: DataProvider):
        self.db = db
        self.data = data_provider

    async def open_position(self, trade_input: dict) -> Position:
        """
        Open a new position from user input.

        Required: symbol, direction (LONG/SHORT), entry_price, quantity
        Optional: stop_loss_price, profit_target_price, custom overrides
        """
        symbol = trade_input["symbol"]
        entry_price = trade_input["entry_price"]
        direction = trade_input["direction"]

        # Get current ATR for dynamic exit levels
        bars = await self.data.get_intraday(symbol)
        atr = self._calc_atr(bars)

        # Get current regime
        detector = RegimeDetector(self.data)
        regime_result = await detector.detect()
        regime = regime_result["regime"]

        # Compute default exit levels
        stop_mult = trade_input.get("atr_stop_multiplier", settings.default_atr_multiplier_stop)
        target_mult = trade_input.get("atr_target_multiplier", settings.default_atr_multiplier_target)

        if direction == "LONG":
            default_stop = entry_price - atr * stop_mult
            default_target = entry_price + atr * target_mult
        else:
            default_stop = entry_price + atr * stop_mult
            default_target = entry_price - atr * target_mult

        position = Position(
            symbol=symbol,
            exchange=trade_input.get("exchange"),
            direction=direction,
            status="OPEN",
            entry_price=entry_price,
            quantity=trade_input["quantity"],
            entry_time=trade_input.get("entry_time", datetime.utcnow()),
            entry_signal_id=trade_input.get("entry_signal_id"),

            # Exit config — user overrides or ATR-based defaults
            stop_loss_price=trade_input.get("stop_loss_price", round(default_stop, 2)),
            profit_target_price=trade_input.get("profit_target_price", round(default_target, 2)),
            stop_loss_pct=trade_input.get("stop_loss_pct", settings.default_stop_loss_pct),
            profit_target_pct=trade_input.get("profit_target_pct", settings.default_profit_target_pct),
            use_atr_exits=trade_input.get("use_atr_exits", True),
            atr_stop_multiplier=stop_mult,
            atr_target_multiplier=target_mult,
            atr_value_at_entry=round(atr, 4),
            eod_exit_enabled=trade_input.get("eod_exit_enabled", True),
            max_hold_bars=trade_input.get("max_hold_bars", settings.max_hold_bars),

            # Initial tracking
            current_price=entry_price,
            unrealized_pnl=0.0,
            unrealized_pnl_pct=0.0,
            high_since_entry=entry_price,
            low_since_entry=entry_price,
            bars_held=0,

            # Context
            regime_at_entry=regime,
        )

        self.db.add(position)
        await self.db.flush()
        await self.db.refresh(position)
        return position

    async def close_position(
        self, position_id: int, exit_price: float, exit_reason: str = "manual"
    ) -> Position:
        """Close a position and record outcome."""
        position = await self.db.get(Position, position_id)
        if not position or position.status != "OPEN":
            raise ValueError("Position not found or already closed")

        # Compute P&L
        if position.direction == "LONG":
            pnl_pct = (exit_price - position.entry_price) / position.entry_price * 100
        else:
            pnl_pct = (position.entry_price - exit_price) / position.entry_price * 100

        pnl_dollar = pnl_pct / 100 * position.entry_price * position.quantity

        # Get current regime for context
        detector = RegimeDetector(self.data)
        regime_result = await detector.detect()

        position.status = "CLOSED"
        position.exit_price = exit_price
        position.exit_time = datetime.utcnow()
        position.exit_reason = exit_reason
        position.realized_pnl = round(pnl_pct, 4)
        position.realized_pnl_pct = round(pnl_pct, 4)
        position.realized_pnl_dollar = round(pnl_dollar, 2)
        position.regime_at_exit = regime_result["regime"]

        await self.db.flush()
        return position

    async def update_exit_levels(self, position_id: int, updates: dict) -> Position:
        """Update stop loss / profit target on an open position."""
        position = await self.db.get(Position, position_id)
        if not position or position.status != "OPEN":
            raise ValueError("Position not found or already closed")

        for field in ["stop_loss_price", "profit_target_price", "stop_loss_pct",
                       "profit_target_pct", "eod_exit_enabled", "max_hold_bars"]:
            if field in updates and updates[field] is not None:
                setattr(position, field, updates[field])

        await self.db.flush()
        return position

    async def get_open_positions(self) -> list[Position]:
        result = await self.db.execute(
            select(Position).where(Position.status == "OPEN")
        )
        return list(result.scalars().all())

    async def get_trade_history(self, days: int = 30) -> list[Position]:
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)
        result = await self.db.execute(
            select(Position)
            .where(Position.status == "CLOSED", Position.exit_time >= cutoff)
            .order_by(Position.exit_time.desc())
        )
        return list(result.scalars().all())

    def _calc_atr(self, bars: list[dict], period: int = 14) -> float:
        """Calculate ATR from bar data."""
        if len(bars) < period + 1:
            return abs(bars[-1]["high"] - bars[-1]["low"])
        trs = []
        for i in range(-period, 0):
            tr = max(
                bars[i]["high"] - bars[i]["low"],
                abs(bars[i]["high"] - bars[i - 1]["close"]),
                abs(bars[i]["low"] - bars[i - 1]["close"]),
            )
            trs.append(tr)
        return sum(trs) / len(trs)
