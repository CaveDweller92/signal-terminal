from datetime import datetime

from sqlalchemy import Integer, String, Float, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class RegimeLog(Base):
    __tablename__ = "regime_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    regime: Mapped[str] = mapped_column(String(30), nullable=False)  # trending_up, trending_down, mean_reverting, volatile_choppy, low_volatility
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    previous_regime: Mapped[str | None] = mapped_column(String(30), nullable=True)
    detection_method: Mapped[str] = mapped_column(String(20), default="hmm")  # hmm, xgb, manual
    features: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # feature values at detection time
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
