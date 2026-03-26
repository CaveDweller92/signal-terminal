from datetime import datetime

from sqlalchemy import Boolean, Float, Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Position(Base):
    """
    An open or closed trading position.

    Lifecycle:
    1. User opens position (manual entry via API/UI)
    2. System attaches exit config (ATR-based stops/targets from current params)
    3. Position monitor continuously evaluates exit conditions
    4. Exit signals pushed via WebSocket
    5. User closes position (manual via API/UI)
    6. Outcome recorded → feeds back into optimizer
    """
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    exchange: Mapped[str | None] = mapped_column(String(20), nullable=True)
    direction: Mapped[str] = mapped_column(String(5), nullable=False)  # LONG or SHORT
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="OPEN", index=True)  # OPEN, CLOSED, EXPIRED

    # Entry info (user-provided)
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    entry_signal_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # FK to signals(id)

    # Exit strategy config at open time
    stop_loss_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    profit_target_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    stop_loss_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    profit_target_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    use_atr_exits: Mapped[bool] = mapped_column(Boolean, default=True)
    atr_stop_multiplier: Mapped[float | None] = mapped_column(Float, default=1.5)
    atr_target_multiplier: Mapped[float | None] = mapped_column(Float, default=2.5)
    atr_value_at_entry: Mapped[float | None] = mapped_column(Float, nullable=True)
    eod_exit_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    max_hold_bars: Mapped[int | None] = mapped_column(Integer, default=60)

    # Live tracking (updated continuously by position monitor)
    current_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    unrealized_pnl: Mapped[float | None] = mapped_column(Float, nullable=True)
    unrealized_pnl_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    high_since_entry: Mapped[float | None] = mapped_column(Float, nullable=True)
    low_since_entry: Mapped[float | None] = mapped_column(Float, nullable=True)
    bars_held: Mapped[int] = mapped_column(Integer, default=0)
    last_updated: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Exit info (filled on close)
    exit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    exit_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    exit_reason: Mapped[str | None] = mapped_column(String(30), nullable=True)
    exit_signal_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    realized_pnl: Mapped[float | None] = mapped_column(Float, nullable=True)
    realized_pnl_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    realized_pnl_dollar: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Context
    regime_at_entry: Mapped[str | None] = mapped_column(String(30), nullable=True)
    regime_at_exit: Mapped[str | None] = mapped_column(String(30), nullable=True)
    config_snapshot_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
