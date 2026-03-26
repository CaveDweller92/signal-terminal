"""
Regime Presets — parameter overrides per market regime.

When the regime detector identifies a shift, these presets are applied
on top of the optimizer's base parameters. The idea: different market
conditions call for different strategy behavior.

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
        "min_signal_strength": 1.5,
        "technical_weight": 0.6,
        "sentiment_weight": 0.25,
        "fundamental_weight": 0.15,
        # Let winners run
        "atr_target_multiplier": 3.0,
        "atr_stop_multiplier": 1.5,
        "max_hold_bars": 90,
    },
    "trending_down": {
        "rsi_oversold": 25,
        "rsi_overbought": 65,
        "min_signal_strength": 2.5,
        "technical_weight": 0.55,
        "sentiment_weight": 0.3,
        "fundamental_weight": 0.15,
        # Tight stops, quick profits
        "atr_target_multiplier": 2.0,
        "atr_stop_multiplier": 1.2,
        "max_hold_bars": 40,
    },
    "mean_reverting": {
        "rsi_oversold": 28,
        "rsi_overbought": 72,
        "min_signal_strength": 1.75,
        "technical_weight": 0.5,
        "sentiment_weight": 0.3,
        "fundamental_weight": 0.2,
        # Take profits at mean
        "atr_target_multiplier": 2.0,
        "atr_stop_multiplier": 1.5,
        "max_hold_bars": 50,
    },
    "volatile_choppy": {
        "rsi_oversold": 22,
        "rsi_overbought": 78,
        "min_signal_strength": 3.0,
        "technical_weight": 0.45,
        "sentiment_weight": 0.35,
        "fundamental_weight": 0.2,
        # Very tight — take any profit, get out fast
        "atr_target_multiplier": 1.5,
        "atr_stop_multiplier": 1.0,
        "max_hold_bars": 25,
    },
    "low_volatility": {
        "rsi_oversold": 32,
        "rsi_overbought": 68,
        "min_signal_strength": 1.5,
        "technical_weight": 0.5,
        "sentiment_weight": 0.3,
        "fundamental_weight": 0.2,
        # Standard exits, low vol = reliable
        "atr_target_multiplier": 2.5,
        "atr_stop_multiplier": 1.5,
        "max_hold_bars": 60,
    },
}


def get_preset(regime: str) -> dict:
    """Get the parameter preset for a given regime, or empty dict if unknown."""
    return dict(REGIME_PRESETS.get(regime, {}))
