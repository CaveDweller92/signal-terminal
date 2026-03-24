from datetime import datetime

from sqlalchemy import Float, Integer, String, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    signal_type: Mapped[str] = mapped_column(String(4), nullable=False)  # BUY, SELL, HOLD
    conviction: Mapped[float] = mapped_column(Float, nullable=False)
    tech_score: Mapped[float] = mapped_column(Float, nullable=False)
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=False)
    fundamental_score: Mapped[float] = mapped_column(Float, nullable=False)
    price_at_signal: Mapped[float] = mapped_column(Float, nullable=False)
    regime_at_signal: Mapped[str | None] = mapped_column(String(30), nullable=True)
    config_snapshot_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reasons: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Suggested exit levels
    suggested_stop_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    suggested_profit_target: Mapped[float | None] = mapped_column(Float, nullable=True)
    atr_at_signal: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Outcome tracking (filled after trade closes)
    outcome: Mapped[str | None] = mapped_column(String(10), nullable=True)  # win, loss, scratch
    exit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    return_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    bars_held: Mapped[int | None] = mapped_column(Integer, nullable=True)
    outcome_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
