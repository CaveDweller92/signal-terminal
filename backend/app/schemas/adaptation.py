from datetime import date, datetime

from pydantic import BaseModel


class ParameterSnapshotResponse(BaseModel):
    id: int
    snapshot_type: str
    trigger: str | None = None

    # Entry parameters
    rsi_period: int
    rsi_overbought: int
    rsi_oversold: int
    ema_fast: int
    ema_slow: int
    volume_multiplier: float
    min_signal_strength: float
    technical_weight: float
    sentiment_weight: float
    fundamental_weight: float

    # Exit parameters
    atr_stop_multiplier: float
    atr_target_multiplier: float
    default_stop_loss_pct: float
    default_profit_target_pct: float
    max_hold_bars: int

    full_config: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MetaReviewResponse(BaseModel):
    id: int
    review_date: date
    regime_at_review: str | None = None
    summary: str
    recommendations: list | dict | None = None
    parameter_adjustments: list | dict | None = None
    exit_strategy_assessment: list | dict | None = None
    signals_generated: int
    signals_correct: int
    avg_return: float | None = None
    regime_accuracy: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
