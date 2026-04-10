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
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.engine.data_provider import DataProvider
from app.engine.regime import RegimeDetector
from app.models.parameter_snapshot import ParameterSnapshot
from app.models.position import Position
from app.models.signal import Signal


class PositionManager:
    def __init__(self, db: AsyncSession, data_provider: DataProvider):
        self.db = db
        self.data = data_provider

    async def _get_active_multipliers(self) -> tuple[float, float]:
        """
        Single source of truth for ATR multipliers — pulls from the latest
        ParameterSnapshot (which is fed by regime presets + optimizer).
        Falls back to .env defaults if no snapshot exists yet.
        """
        try:
            result = await self.db.execute(
                select(ParameterSnapshot)
                .order_by(ParameterSnapshot.created_at.desc())
                .limit(1)
            )
            snapshot = result.scalar_one_or_none()
            if snapshot and getattr(snapshot, "full_config", None):
                cfg = snapshot.full_config
                return (
                    float(cfg.get("atr_stop_multiplier", settings.default_atr_multiplier_stop)),
                    float(cfg.get("atr_target_multiplier", settings.default_atr_multiplier_target)),
                )
        except Exception:
            pass
        return (
            settings.default_atr_multiplier_stop,
            settings.default_atr_multiplier_target,
        )

    def _apply_exit_caps(
        self, entry_price: float, stop: float, target: float, is_long: bool
    ) -> tuple[float, float]:
        """Apply hard caps so volatile stocks can't get absurd exit levels."""
        max_stop_pct = settings.max_stop_loss_pct / 100
        max_target_pct = settings.max_profit_target_pct / 100

        if is_long:
            min_stop = entry_price * (1 - max_stop_pct)
            max_target = entry_price * (1 + max_target_pct)
            if stop < min_stop:
                stop = min_stop
            if target > max_target:
                target = max_target
        else:
            max_stop = entry_price * (1 + max_stop_pct)
            min_target = entry_price * (1 - max_target_pct)
            if stop > max_stop:
                stop = max_stop
            if target < min_target:
                target = min_target

        return round(stop, 2), round(target, 2)

    async def open_position(self, trade_input: dict) -> Position:
        """
        Open a new position from user input.

        Required: symbol, direction (LONG/SHORT), entry_price, quantity
        Optional: stop_loss_price, profit_target_price, custom overrides

        Exit level priority:
          1. User-provided stop/target (highest priority)
          2. Linked signal's stored stop/target (so position matches what user clicked)
          3. ATR × active regime multipliers (with hard caps applied)
        """
        symbol = trade_input["symbol"]
        entry_price = trade_input["entry_price"]
        direction = trade_input["direction"]
        is_long = direction == "LONG"

        # Get current ATR from daily bars — matches SignalAnalyzer
        daily = await self.data.get_daily(symbol)
        bars = await self.data.get_intraday(symbol)
        if daily:
            atr = self._calc_atr(daily)
        elif bars:
            atr = self._calc_atr(bars)
        else:
            atr = entry_price * 0.02  # fallback: 2% of price

        # Get current regime
        detector = RegimeDetector(self.data)
        regime_result = await detector.detect()
        regime = regime_result["regime"]

        # Pull multipliers from the SAME source the analyzer uses
        active_stop_mult, active_target_mult = await self._get_active_multipliers()
        stop_mult = trade_input.get("atr_stop_multiplier", active_stop_mult)
        target_mult = trade_input.get("atr_target_multiplier", active_target_mult)

        # Auto-link to today's signal for this symbol (if not manually provided)
        entry_signal_id = trade_input.get("entry_signal_id")
        if not entry_signal_id:
            from datetime import date
            today = date.today()
            expected_type = "BUY" if is_long else "SELL"
            sig_result = await self.db.execute(
                select(Signal.id)
                .where(Signal.symbol == symbol)
                .where(Signal.signal_type == expected_type)
                .where(func.date(Signal.created_at) == today)
                .order_by(Signal.created_at.desc())
                .limit(1)
            )
            entry_signal_id = sig_result.scalar_one_or_none()

        # If we have a linked signal, prefer ITS stored stop/target so the
        # position matches exactly what the user clicked on in the UI.
        signal_stop = None
        signal_target = None
        if entry_signal_id:
            signal_obj = await self.db.get(Signal, entry_signal_id)
            if signal_obj:
                signal_stop = signal_obj.suggested_stop_loss
                signal_target = signal_obj.suggested_profit_target

        if signal_stop is not None and signal_target is not None:
            default_stop = signal_stop
            default_target = signal_target
        elif is_long:
            default_stop = entry_price - atr * stop_mult
            default_target = entry_price + atr * target_mult
        else:
            default_stop = entry_price + atr * stop_mult
            default_target = entry_price - atr * target_mult

        # Apply hard caps to whatever we computed
        default_stop, default_target = self._apply_exit_caps(
            entry_price, default_stop, default_target, is_long,
        )

        position = Position(
            symbol=symbol,
            exchange=trade_input.get("exchange"),
            direction=direction,
            status="OPEN",
            entry_price=entry_price,
            quantity=trade_input["quantity"],
            entry_time=trade_input.get("entry_time", datetime.utcnow()),
            entry_signal_id=entry_signal_id,

            # Exit config — user overrides or ATR-based defaults
            stop_loss_price=trade_input.get("stop_loss_price", round(default_stop, 2)),
            profit_target_price=trade_input.get("profit_target_price", round(default_target, 2)),
            stop_loss_pct=trade_input.get("stop_loss_pct", settings.default_stop_loss_pct),
            profit_target_pct=trade_input.get("profit_target_pct", settings.default_profit_target_pct),
            use_atr_exits=trade_input.get("use_atr_exits", True),
            atr_stop_multiplier=stop_mult,
            atr_target_multiplier=target_mult,
            atr_value_at_entry=round(atr, 4),
            eod_exit_enabled=trade_input.get("eod_exit_enabled", False),
            max_hold_days=trade_input.get("max_hold_days", settings.max_hold_days),

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

        # Update linked signal outcome
        if position.entry_signal_id:
            signal = await self.db.get(Signal, position.entry_signal_id)
            if signal:
                if pnl_pct > 0.5:
                    signal.outcome = "win"
                elif pnl_pct < -0.5:
                    signal.outcome = "loss"
                else:
                    signal.outcome = "scratch"
                signal.exit_price = exit_price
                signal.return_pct = round(pnl_pct, 4)
                days_held = (datetime.utcnow() - position.entry_time).days if position.entry_time else 0
                signal.bars_held = max(days_held, 1)
                signal.outcome_at = datetime.utcnow()

        await self.db.flush()
        return position

    async def edit_position(self, position_id: int, updates: dict) -> Position:
        """Edit core position fields. Auto-recalculates stop/target if entry price or direction changes."""
        position = await self.db.get(Position, position_id)
        if not position or position.status != "OPEN":
            raise ValueError("Position not found or already closed")

        for field in ["entry_price", "quantity", "direction",
                       "stop_loss_price", "profit_target_price"]:
            if field in updates and updates[field] is not None:
                setattr(position, field, updates[field])

        # Auto-recalculate stop/target when entry price or direction changes
        # (unless the user explicitly provided new stop/target values)
        recalc = "entry_price" in updates or "direction" in updates
        user_set_sl = "stop_loss_price" in updates
        user_set_pt = "profit_target_price" in updates

        # Recalculate P&L with updated entry price / direction / quantity
        price = position.current_price or position.entry_price
        if position.direction == "LONG":
            pnl_pct = (price - position.entry_price) / position.entry_price * 100
            pnl_dollar = (price - position.entry_price) * position.quantity
        else:
            pnl_pct = (position.entry_price - price) / position.entry_price * 100
            pnl_dollar = (position.entry_price - price) * position.quantity
        position.unrealized_pnl_pct = round(pnl_pct, 4)
        position.unrealized_pnl = round(pnl_dollar, 2)

        if recalc and (not user_set_sl or not user_set_pt):
            atr = position.atr_value_at_entry
            if not atr:
                daily = await self.data.get_daily(position.symbol)
                atr = self._calc_atr(daily) if daily else position.entry_price * 0.02

            entry = position.entry_price
            stop_mult = position.atr_stop_multiplier or settings.default_atr_multiplier_stop
            target_mult = position.atr_target_multiplier or settings.default_atr_multiplier_target
            is_long = position.direction == "LONG"

            if is_long:
                new_sl = entry - atr * stop_mult
                new_pt = entry + atr * target_mult
            else:
                new_sl = entry + atr * stop_mult
                new_pt = entry - atr * target_mult

            # Apply hard caps so volatile stocks can't get absurd levels
            new_sl, new_pt = self._apply_exit_caps(entry, new_sl, new_pt, is_long)

            if not user_set_sl:
                position.stop_loss_price = new_sl
            if not user_set_pt:
                position.profit_target_price = new_pt

        await self.db.flush()
        return position

    async def update_exit_levels(self, position_id: int, updates: dict) -> Position:
        """Update stop loss / profit target on an open position."""
        position = await self.db.get(Position, position_id)
        if not position or position.status != "OPEN":
            raise ValueError("Position not found or already closed")

        for field in ["stop_loss_price", "profit_target_price", "stop_loss_pct",
                       "profit_target_pct", "eod_exit_enabled", "max_hold_days"]:
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
