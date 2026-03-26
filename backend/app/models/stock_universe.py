from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class StockUniverse(Base):
    """
    Master list of tradable stocks across all universes.
    ~830 stocks: S&P 500 + NASDAQ 100 + TSX/TSXV (with overlap removed).
    Refreshed weekly via universe_update task.
    """
    __tablename__ = "stock_universe"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    exchange: Mapped[str] = mapped_column(String(20), nullable=False)
    universe: Mapped[str] = mapped_column(String(20), nullable=False)  # sp500, nasdaq100, tsx
    sector: Mapped[str | None] = mapped_column(String(50), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    market_cap: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    avg_volume_30d: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    country: Mapped[str] = mapped_column(String(5), default="US")
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        # Unique constraint on symbol + exchange (AAPL on NYSE vs TSX)
        {"sqlite_autoincrement": True},
    )
