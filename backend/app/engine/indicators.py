import numpy as np


def calc_ema(closes: np.ndarray, period: int) -> np.ndarray:
    """
    Exponential Moving Average.

    Gives more weight to recent prices. A 9-period EMA reacts faster
    than a 21-period EMA — when the fast crosses above the slow,
    that's a bullish signal (and vice versa).

    Returns array same length as input, with early values using SMA as seed.
    """
    if len(closes) < period:
        return np.full_like(closes, np.nan)

    ema = np.empty_like(closes, dtype=float)
    ema[:period] = np.nan
    ema[period - 1] = np.mean(closes[:period])  # Seed with SMA

    multiplier = 2.0 / (period + 1)
    for i in range(period, len(closes)):
        ema[i] = closes[i] * multiplier + ema[i - 1] * (1 - multiplier)

    return ema


def calc_rsi(closes: np.ndarray, period: int = 14) -> np.ndarray:
    """
    Relative Strength Index (0-100).

    Measures momentum by comparing average gains vs average losses
    over N periods.

    > 70 = overbought (price may be too high, potential sell)
    < 30 = oversold   (price may be too low, potential buy)

    Uses Wilder's smoothing method (exponential moving average of gains/losses).
    """
    if len(closes) < period + 1:
        return np.full_like(closes, np.nan)

    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    rsi = np.full(len(closes), np.nan)

    # Seed: simple average of first N periods
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    if avg_loss == 0:
        rsi[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi[period] = 100.0 - (100.0 / (1.0 + rs))

    # Wilder's smoothing for remaining periods
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            rsi[i + 1] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i + 1] = 100.0 - (100.0 / (1.0 + rs))

    return rsi


def calc_macd(
    closes: np.ndarray,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Moving Average Convergence Divergence.

    Three components:
    - MACD line:     fast EMA - slow EMA (measures trend momentum)
    - Signal line:   EMA of MACD line (smoothed trigger)
    - Histogram:     MACD - Signal (positive = bullish momentum, negative = bearish)

    Key signals:
    - Histogram crosses zero upward → bullish (buy)
    - Histogram crosses zero downward → bearish (sell)
    - Divergence between price and MACD → trend weakening

    Returns (macd_line, signal_line, histogram), each same length as input.
    """
    ema_fast = calc_ema(closes, fast_period)
    ema_slow = calc_ema(closes, slow_period)

    macd_line = ema_fast - ema_slow

    # Signal line is EMA of MACD line (only where MACD is valid)
    signal_line = np.full_like(closes, np.nan)
    valid_start = slow_period - 1  # First valid MACD value

    if len(closes) > valid_start + signal_period:
        macd_valid = macd_line[valid_start:]
        signal_valid = calc_ema(macd_valid, signal_period)
        signal_line[valid_start:] = signal_valid

    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram


def calc_atr(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    period: int = 14,
) -> np.ndarray:
    """
    Average True Range — measures volatility.

    True Range is the largest of:
    1. Current high - current low
    2. |Current high - previous close|
    3. |Current low - previous close|

    ATR smooths this over N periods. Used to set dynamic stop losses
    and profit targets that adapt to how much a stock actually moves.

    Higher ATR = wider stops (volatile stock needs room to breathe)
    Lower ATR  = tighter stops (calm stock, less noise)
    """
    if len(closes) < 2:
        return np.full_like(closes, np.nan)

    atr = np.full(len(closes), np.nan)

    # True Range for each bar (starting from index 1)
    tr = np.maximum(
        highs[1:] - lows[1:],
        np.maximum(
            np.abs(highs[1:] - closes[:-1]),
            np.abs(lows[1:] - closes[:-1]),
        ),
    )

    if len(tr) < period:
        return atr

    # Seed with simple average
    atr[period] = np.mean(tr[:period])

    # Wilder's smoothing
    for i in range(period, len(tr)):
        atr[i + 1] = (atr[i] * (period - 1) + tr[i]) / period

    return atr


def calc_volume_ratio(volumes: np.ndarray, period: int = 20) -> np.ndarray:
    """
    Volume ratio = current volume / average volume over N periods.

    > 1.5 = volume spike (unusual activity, often institutional)
    > 2.0 = significant spike (strong interest, confirms price move)
    < 0.5 = low volume (move may not be trustworthy)

    Used as a confirmation filter — a BUY signal on high volume
    is more reliable than one on thin volume.
    """
    if len(volumes) < period:
        return np.full_like(volumes, np.nan, dtype=float)

    ratio = np.full(len(volumes), np.nan, dtype=float)

    for i in range(period, len(volumes)):
        avg = np.mean(volumes[i - period:i])
        if avg > 0:
            ratio[i] = volumes[i] / avg
        else:
            ratio[i] = 0.0

    return ratio


def detect_ema_crossover(
    closes: np.ndarray, fast_period: int = 9, slow_period: int = 21
) -> dict:
    """
    Detects EMA crossovers — the most basic trend signal.

    Bullish cross: fast EMA crosses ABOVE slow EMA (uptrend starting)
    Bearish cross: fast EMA crosses BELOW slow EMA (downtrend starting)

    Returns current state and whether a cross just happened.
    """
    ema_fast = calc_ema(closes, fast_period)
    ema_slow = calc_ema(closes, slow_period)

    if np.isnan(ema_fast[-1]) or np.isnan(ema_slow[-1]):
        return {"crossover": "none", "just_crossed": False}

    current_above = ema_fast[-1] > ema_slow[-1]

    # Check if it just crossed (previous bar was opposite)
    just_crossed = False
    if len(closes) >= 2 and not np.isnan(ema_fast[-2]) and not np.isnan(ema_slow[-2]):
        prev_above = ema_fast[-2] > ema_slow[-2]
        just_crossed = current_above != prev_above

    return {
        "crossover": "bullish" if current_above else "bearish",
        "just_crossed": just_crossed,
        "ema_fast": float(ema_fast[-1]),
        "ema_slow": float(ema_slow[-1]),
        "spread": float(ema_fast[-1] - ema_slow[-1]),
    }
