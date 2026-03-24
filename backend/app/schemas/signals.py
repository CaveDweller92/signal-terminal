from datetime import datetime

from pydantic import BaseModel, Field


class SignalResponse(BaseModel):
    id: int
    symbol: str
    signal_type: str
    conviction: float
    tech_score: float
    sentiment_score: float
    fundamental_score: float
    price_at_signal: float
    regime_at_signal: str | None = None
    reasons: dict | None = None
    suggested_stop_loss: float | None = None
    suggested_profit_target: float | None = None
    atr_at_signal: float | None = None
    created_at: datetime

    # Outcome (None until trade closes)
    outcome: str | None = None
    exit_price: float | None = None
    return_pct: float | None = None
    bars_held: int | None = None

    model_config = {"from_attributes": True}


class SignalListResponse(BaseModel):
    signals: list[SignalResponse]
    count: int
