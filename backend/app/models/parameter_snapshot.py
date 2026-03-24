from datetime import datetime

from sqlalchemy import Integer, String, Float, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class ParameterSnapshot(Base):
    __tablename__ = "parameter_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_type: Mapped[str] = mapped_column(String(20), nullable=False)  # scheduled, regime_change, manual
    trigger: Mapped[str | None] = mapped_column(String(50), nullable=True)  # what caused this snapshot

    # Entry parameters
    rsi_period: Mapped[int] = mapped_column(Integer, default=14)
    rsi_overbought: Mapped[int] = mapped_column(Integer, default=70)
    rsi_oversold: Mapped[int] = mapped_column(Integer, default=30)
    ema_fast: Mapped[int] = mapped_column(Integer, default=9)
    ema_slow: Mapped[int] = mapped_column(Integer, default=21)
    volume_multiplier: Mapped[float] = mapped_column(Float, default=1.5)
    min_signal_strength: Mapped[float] = mapped_column(Float, default=2.0)
    technical_weight: Mapped[float] = mapped_column(Float, default=0.5)
    sentiment_weight: Mapped[float] = mapped_column(Float, default=0.3)
    fundamental_weight: Mapped[float] = mapped_column(Float, default=0.2)

    # Exit parameters
    atr_stop_multiplier: Mapped[float] = mapped_column(Float, default=1.5)
    atr_target_multiplier: Mapped[float] = mapped_column(Float, default=2.5)
    default_stop_loss_pct: Mapped[float] = mapped_column(Float, default=2.0)
    default_profit_target_pct: Mapped[float] = mapped_column(Float, default=3.0)
    max_hold_bars: Mapped[int] = mapped_column(Integer, default=60)

    # Full config as JSON (for forward-compatibility)
    full_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
