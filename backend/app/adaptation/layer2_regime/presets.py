"""
Regime Presets — parameter overrides per market regime (swing trading).

When the regime detector identifies a shift, these presets are applied
on top of the optimizer's base parameters. The idea: different market
conditions call for different strategy behavior.

All max_hold_days values are in trading days.
ATR multipliers are calibrated for daily ATR.

Trending up → let winners run (wide targets, normal stops)
Trending down → tight stops, quick profits
Mean reverting → take profits at mean
Volatile choppy → very tight everything, reduce exposure
Low volatility → standard parameters, reliable signals
"""

REGIME_PRESETS: dict[str, dict] = {
    "trending_up": {
        "rsi_oversold": 35,
        "rsi_overbought": 80,
        "min_signal_strength": 1.2,
        "technical_weight": 0.6,
        "sentiment_weight": 0.25,
        "fundamental_weight": 0.15,
        # Let winners run — wide targets for multi-day trends
        "atr_target_multiplier": 5.0,
        "atr_stop_multiplier": 2.5,
        "max_hold_days": 40,  # ~8 weeks
    },
    "trending_down": {
        "rsi_oversold": 25,
        "rsi_overbought": 65,
        "min_signal_strength": 1.2,
        "technical_weight": 0.55,
        "sentiment_weight": 0.3,
        "fundamental_weight": 0.15,
        # Tight stops, take profits quickly
        "atr_target_multiplier": 3.0,
        "atr_stop_multiplier": 2.0,
        "max_hold_days": 15,  # ~3 weeks
    },
    "mean_reverting": {
        "rsi_oversold": 28,
        "rsi_overbought": 72,
        "min_signal_strength": 1.5,
        "technical_weight": 0.5,
        "sentiment_weight": 0.3,
        "fundamental_weight": 0.2,
        # Take profits at mean
        "atr_target_multiplier": 3.5,
        "atr_stop_multiplier": 2.5,
        "max_hold_days": 20,  # ~4 weeks
    },
    "volatile_choppy": {
        "rsi_oversold": 22,
        "rsi_overbought": 78,
        "min_signal_strength": 1.8,
        "technical_weight": 0.45,
        "sentiment_weight": 0.35,
        "fundamental_weight": 0.2,
        # Cautious — smaller positions, tighter exits
        "atr_target_multiplier": 2.5,
        "atr_stop_multiplier": 1.5,
        "max_hold_days": 10,  # ~2 weeks
    },
    "low_volatility": {
        "rsi_oversold": 32,
        "rsi_overbought": 68,
        "min_signal_strength": 1.2,
        "technical_weight": 0.5,
        "sentiment_weight": 0.3,
        "fundamental_weight": 0.2,
        # Reliable signals, standard swing parameters
        "atr_target_multiplier": 4.0,
        "atr_stop_multiplier": 2.5,
        "max_hold_days": 25,  # ~5 weeks
    },
}


def get_preset(regime: str) -> dict:
    """Get the parameter preset for a given regime, or empty dict if unknown."""
    return dict(REGIME_PRESETS.get(regime, {}))
