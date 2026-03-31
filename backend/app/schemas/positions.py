from datetime import datetime

from pydantic import BaseModel, Field


class TradeInput(BaseModel):
    """Request to open a new position."""
    symbol: str
    direction: str = Field(pattern="^(LONG|SHORT)$")
    entry_price: float = Field(gt=0)
    quantity: int = Field(gt=0)
    exchange: str | None = None
    entry_signal_id: int | None = None
    entry_time: datetime | None = None

    # Optional exit overrides (system computes defaults if not provided)
    stop_loss_price: float | None = None
    profit_target_price: float | None = None
    stop_loss_pct: float | None = Field(None, ge=0.1, le=20.0)
    profit_target_pct: float | None = Field(None, ge=0.1, le=50.0)
    use_atr_exits: bool = True
    eod_exit_enabled: bool = False
    max_hold_days: int | None = Field(None, ge=1, le=120)  # trading days


class CloseInput(BaseModel):
    """Request to close an open position."""
    exit_price: float = Field(gt=0)
    exit_reason: str | None = "manual"


class ExitUpdateInput(BaseModel):
    """Update exit levels on an open position."""
    stop_loss_price: float | None = None
    profit_target_price: float | None = None
    stop_loss_pct: float | None = Field(None, ge=0.1, le=20.0)
    profit_target_pct: float | None = Field(None, ge=0.1, le=50.0)
    eod_exit_enabled: bool | None = None
    max_hold_days: int | None = Field(None, ge=1, le=120)  # trading days


class PositionEditInput(BaseModel):
    """Edit core position fields (for correcting data entry errors)."""
    entry_price: float | None = Field(None, gt=0)
    quantity: int | None = Field(None, gt=0)
    direction: str | None = Field(None, pattern="^(LONG|SHORT)$")
    stop_loss_price: float | None = None
    profit_target_price: float | None = None


class PositionResponse(BaseModel):
    id: int
    symbol: str
    exchange: str | None = None
    direction: str
    status: str
    entry_price: float
    quantity: int
    entry_time: datetime
    entry_signal_id: int | None = None

    # Exit config
    stop_loss_price: float | None = None
    profit_target_price: float | None = None
    stop_loss_pct: float | None = None
    profit_target_pct: float | None = None
    use_atr_exits: bool = True
    atr_value_at_entry: float | None = None
    eod_exit_enabled: bool = False
    max_hold_days: int | None = None  # trading days

    # Live tracking
    current_price: float | None = None
    unrealized_pnl: float | None = None
    unrealized_pnl_pct: float | None = None
    high_since_entry: float | None = None
    low_since_entry: float | None = None
    bars_held: int = 0

    # Exit info (filled when closed)
    exit_price: float | None = None
    exit_time: datetime | None = None
    exit_reason: str | None = None
    realized_pnl: float | None = None
    realized_pnl_pct: float | None = None
    realized_pnl_dollar: float | None = None

    # Context
    regime_at_entry: str | None = None
    regime_at_exit: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ExitSignalResponse(BaseModel):
    id: int
    position_id: int
    symbol: str
    exit_type: str
    urgency: str
    trigger_price: float | None = None
    current_price: float
    message: str
    details: dict | None = None
    acknowledged: bool = False
    acted_on: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class TradeStatsResponse(BaseModel):
    """Aggregate stats for closed trades."""
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float | None = None
    avg_return_pct: float | None = None
    avg_winner_pct: float | None = None
    avg_loser_pct: float | None = None
    best_trade_pct: float | None = None
    worst_trade_pct: float | None = None
    profit_factor: float | None = None
    avg_bars_held: float | None = None
