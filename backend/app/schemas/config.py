from pydantic import BaseModel, Field


class ConfigResponse(BaseModel):
    """Current strategy configuration — swing trading defaults."""
    # Entry parameters
    rsi_period: int = 14
    rsi_overbought: int = 70
    rsi_oversold: int = 30
    ema_fast: int = 10
    ema_slow: int = 50
    volume_multiplier: float = 1.3
    min_signal_strength: float = 1.5
    technical_weight: float = 0.5
    sentiment_weight: float = 0.3
    fundamental_weight: float = 0.2

    # Exit parameters
    atr_stop_multiplier: float = 2.5
    atr_target_multiplier: float = 4.0
    default_stop_loss_pct: float = 5.0
    default_profit_target_pct: float = 10.0
    max_hold_days: int = 25  # trading days

    model_config = {"from_attributes": True}


class ConfigUpdateRequest(BaseModel):
    """Partial update — only include fields you want to change."""
    rsi_period: int | None = None
    rsi_overbought: int | None = None
    rsi_oversold: int | None = None
    ema_fast: int | None = None
    ema_slow: int | None = None
    volume_multiplier: float | None = Field(None, ge=0.1, le=10.0)
    min_signal_strength: float | None = Field(None, ge=0.0, le=5.0)
    technical_weight: float | None = Field(None, ge=0.0, le=1.0)
    sentiment_weight: float | None = Field(None, ge=0.0, le=1.0)
    fundamental_weight: float | None = Field(None, ge=0.0, le=1.0)
    atr_stop_multiplier: float | None = Field(None, ge=0.5, le=5.0)
    atr_target_multiplier: float | None = Field(None, ge=1.0, le=10.0)
    default_stop_loss_pct: float | None = Field(None, ge=1.0, le=20.0)
    default_profit_target_pct: float | None = Field(None, ge=2.0, le=50.0)
    max_hold_days: int | None = Field(None, ge=1, le=120)  # trading days
