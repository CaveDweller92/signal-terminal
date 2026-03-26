from datetime import date, datetime

from sqlalchemy import Boolean, Date, Float, Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class ScreenerResult(Base):
    """
    Pre-market screener output. One row per stock per scan date.
    Top 30 stocks surface from ~830 scanned.
    Scored on 6 dimensions: volume, gap, technical, fundamental, news, sector momentum.
    """
    __tablename__ = "screener_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scan_date: Mapped[date] = mapped_column(Date, nullable=False)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    exchange: Mapped[str | None] = mapped_column(String(20), nullable=True)
    composite_score: Mapped[float] = mapped_column(Float, nullable=False)
    volume_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    gap_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    technical_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    fundamental_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    news_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    sector_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    premarket_gap_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    relative_volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    sector: Mapped[str | None] = mapped_column(String(50), nullable=True)
    has_catalyst: Mapped[bool] = mapped_column(Boolean, default=False)
    catalyst_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
