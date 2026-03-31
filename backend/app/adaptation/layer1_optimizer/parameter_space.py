"""
Parameter Space — defines the bounds and defaults for all tunable parameters.

The optimizer searches within these bounds. Safety constraints prevent
extreme values that could blow up the strategy.

Swing trading: daily bars, max_hold_days = trading days.
"""

from dataclasses import dataclass


@dataclass
class ParamBound:
    name: str
    min_val: float
    max_val: float
    step: float
    default: float


# All tunable parameters with their bounds (swing trading)
PARAMETER_SPACE = [
    # Entry parameters
    ParamBound("rsi_period",            5,   30,  1,    14),
    ParamBound("rsi_overbought",        60,  90,  1,    70),
    ParamBound("rsi_oversold",          10,  40,  1,    30),
    ParamBound("ema_fast",              5,   20,  1,    10),
    ParamBound("ema_slow",              20,  100, 5,    50),
    ParamBound("volume_multiplier",     1.0, 3.0, 0.1,  1.3),
    ParamBound("min_signal_strength",   0.5, 3.0, 0.25, 1.5),
    ParamBound("technical_weight",      0.0, 1.0, 0.05, 0.5),
    ParamBound("sentiment_weight",      0.0, 1.0, 0.05, 0.3),
    ParamBound("fundamental_weight",    0.0, 1.0, 0.05, 0.2),

    # Exit parameters (swing trading — daily ATR, hold in days)
    ParamBound("atr_stop_multiplier",   1.0, 5.0, 0.25, 2.5),
    ParamBound("atr_target_multiplier", 2.0, 8.0, 0.25, 4.0),
    ParamBound("default_stop_loss_pct", 2.0, 15.0, 0.5, 5.0),
    ParamBound("default_profit_target_pct", 5.0, 25.0, 0.5, 10.0),
    ParamBound("max_hold_days",         5,   60,  5,    25),  # trading days
]

PARAM_BOUNDS = {p.name: p for p in PARAMETER_SPACE}


def get_defaults() -> dict:
    """Return default parameter values."""
    return {p.name: p.default for p in PARAMETER_SPACE}


def clamp_params(params: dict) -> dict:
    """Clamp parameter values to their valid bounds."""
    clamped = {}
    for name, value in params.items():
        if name in PARAM_BOUNDS:
            bound = PARAM_BOUNDS[name]
            clamped[name] = max(bound.min_val, min(bound.max_val, value))
        else:
            clamped[name] = value
    return clamped


def validate_weights(params: dict) -> dict:
    """Ensure technical + sentiment + fundamental weights sum to 1.0."""
    tw = params.get("technical_weight", 0.5)
    sw = params.get("sentiment_weight", 0.3)
    fw = params.get("fundamental_weight", 0.2)
    total = tw + sw + fw

    if total > 0 and abs(total - 1.0) > 0.01:
        params["technical_weight"] = round(tw / total, 3)
        params["sentiment_weight"] = round(sw / total, 3)
        params["fundamental_weight"] = round(fw / total, 3)

    return params
