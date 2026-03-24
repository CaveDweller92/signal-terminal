from datetime import date, datetime

from sqlalchemy import Integer, String, Float, Date, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class DailyPerformance(Base):
    __tablename__ = "daily_performance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    perf_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)

    # Signal stats
    total_signals: Mapped[int] = mapped_column(Integer, default=0)
    buy_signals: Mapped[int] = mapped_column(Integer, default=0)
    sell_signals: Mapped[int] = mapped_column(Integer, default=0)
    signals_correct: Mapped[int] = mapped_column(Integer, default=0)
    signals_incorrect: Mapped[int] = mapped_column(Integer, default=0)
    win_rate: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Returns
    avg_return_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    best_return_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    worst_return_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_return_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Context
    regime: Mapped[str | None] = mapped_column(String(30), nullable=True)
    config_snapshot_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # per-symbol stats

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
