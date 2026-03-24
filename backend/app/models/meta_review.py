from datetime import date, datetime

from sqlalchemy import Integer, String, Float, Date, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class MetaReview(Base):
    __tablename__ = "meta_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    review_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    regime_at_review: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # Claude's analysis
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    recommendations: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    parameter_adjustments: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    exit_strategy_assessment: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Performance context
    signals_generated: Mapped[int] = mapped_column(Integer, default=0)
    signals_correct: Mapped[int] = mapped_column(Integer, default=0)
    avg_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    regime_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
