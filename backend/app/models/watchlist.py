from datetime import date, datetime

from sqlalchemy import Boolean, Date, Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class DailyWatchlist(Base):
    """
    Claude-curated daily watchlist. 12 picks per day with AI reasoning.
    Source can be 'ai' (Claude picked), 'screener' (auto from top 30),
    or 'user' (manually added).
    """
    __tablename__ = "daily_watchlist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    watch_date: Mapped[date] = mapped_column(Date, nullable=False)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    exchange: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # ai, screener, user
    ai_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    screener_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sector: Mapped[str | None] = mapped_column(String(50), nullable=True)
    regime_at_pick: Mapped[str | None] = mapped_column(String(30), nullable=True)
    signals_generated: Mapped[int] = mapped_column(Integer, default=0)
    signals_won: Mapped[int] = mapped_column(Integer, default=0)
    user_added: Mapped[bool] = mapped_column(Boolean, default=False)
    user_removed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
