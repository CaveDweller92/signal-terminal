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
        "just_crossed": bool(just_crossed),
        "ema_fast": float(ema_fast[-1]),
        "ema_slow": float(ema_slow[-1]),
        "spread": float(ema_fast[-1] - ema_slow[-1]),
    }


def calc_bollinger_bands(
    closes: np.ndarray, period: int = 20, num_std: float = 2.0
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Bollinger Bands — price channel based on standard deviation.

    Returns (upper, middle, lower, pct_b) arrays.
    %B = (price - lower) / (upper - lower)
      > 1.0 = above upper band (overbought)
      < 0.0 = below lower band (oversold)
      ~0.5  = at the middle band
    """
    if len(closes) < period:
        nans = np.full_like(closes, np.nan)
        return nans, nans, nans, nans

    middle = np.full_like(closes, np.nan, dtype=float)
    upper = np.full_like(closes, np.nan, dtype=float)
    lower = np.full_like(closes, np.nan, dtype=float)
    pct_b = np.full_like(closes, np.nan, dtype=float)

    for i in range(period - 1, len(closes)):
        window = closes[i - period + 1:i + 1]
        sma = np.mean(window)
        std = np.std(window, ddof=0)

        middle[i] = sma
        upper[i] = sma + num_std * std
        lower[i] = sma - num_std * std

        band_width = upper[i] - lower[i]
        if band_width > 0:
            pct_b[i] = (closes[i] - lower[i]) / band_width
        else:
            pct_b[i] = 0.5

    return upper, middle, lower, pct_b


def calc_stochastic(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    k_period: int = 14,
    d_period: int = 3,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Stochastic Oscillator (%K and %D).

    %K = (close - lowest_low) / (highest_high - lowest_low) * 100
    %D = SMA of %K over d_period

    > 80 = overbought
    < 20 = oversold
    %K crossing above %D = bullish, below = bearish
    """
    n = len(closes)
    if n < k_period:
        return np.full(n, np.nan), np.full(n, np.nan)

    k_line = np.full(n, np.nan, dtype=float)

    for i in range(k_period - 1, n):
        window_high = np.max(highs[i - k_period + 1:i + 1])
        window_low = np.min(lows[i - k_period + 1:i + 1])
        range_val = window_high - window_low

        if range_val > 0:
            k_line[i] = (closes[i] - window_low) / range_val * 100
        else:
            k_line[i] = 50.0

    # %D is SMA of %K
    d_line = np.full(n, np.nan, dtype=float)
    for i in range(k_period - 1 + d_period - 1, n):
        window = k_line[i - d_period + 1:i + 1]
        if not np.any(np.isnan(window)):
            d_line[i] = np.mean(window)

    return k_line, d_line


def calc_adx(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    period: int = 14,
) -> np.ndarray:
    """
    Average Directional Index — measures trend strength (0-100).

    < 20 = weak/no trend (range-bound market)
    20-40 = developing trend
    > 40 = strong trend
    > 60 = very strong trend

    ADX doesn't indicate direction, just how strong the trend is.
    """
    n = len(closes)
    if n < period * 2 + 1:
        return np.full(n, np.nan)

    # +DM and -DM
    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)
    tr = np.zeros(n)

    for i in range(1, n):
        up_move = highs[i] - highs[i - 1]
        down_move = lows[i - 1] - lows[i]

        if up_move > down_move and up_move > 0:
            plus_dm[i] = up_move
        if down_move > up_move and down_move > 0:
            minus_dm[i] = down_move

        tr[i] = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )

    # Smooth with Wilder's method
    smoothed_plus_dm = np.full(n, np.nan, dtype=float)
    smoothed_minus_dm = np.full(n, np.nan, dtype=float)
    smoothed_tr = np.full(n, np.nan, dtype=float)

    smoothed_plus_dm[period] = np.sum(plus_dm[1:period + 1])
    smoothed_minus_dm[period] = np.sum(minus_dm[1:period + 1])
    smoothed_tr[period] = np.sum(tr[1:period + 1])

    for i in range(period + 1, n):
        smoothed_plus_dm[i] = smoothed_plus_dm[i - 1] - smoothed_plus_dm[i - 1] / period + plus_dm[i]
        smoothed_minus_dm[i] = smoothed_minus_dm[i - 1] - smoothed_minus_dm[i - 1] / period + minus_dm[i]
        smoothed_tr[i] = smoothed_tr[i - 1] - smoothed_tr[i - 1] / period + tr[i]

    # +DI and -DI
    plus_di = np.full(n, np.nan, dtype=float)
    minus_di = np.full(n, np.nan, dtype=float)
    dx = np.full(n, np.nan, dtype=float)

    for i in range(period, n):
        if smoothed_tr[i] > 0:
            plus_di[i] = 100 * smoothed_plus_dm[i] / smoothed_tr[i]
            minus_di[i] = 100 * smoothed_minus_dm[i] / smoothed_tr[i]
        else:
            plus_di[i] = 0
            minus_di[i] = 0

        di_sum = plus_di[i] + minus_di[i]
        if di_sum > 0:
            dx[i] = 100 * abs(plus_di[i] - minus_di[i]) / di_sum
        else:
            dx[i] = 0

    # ADX = smoothed DX
    adx = np.full(n, np.nan, dtype=float)
    adx_start = period * 2
    if adx_start < n:
        adx[adx_start] = np.nanmean(dx[period:adx_start + 1])
        for i in range(adx_start + 1, n):
            if not np.isnan(adx[i - 1]) and not np.isnan(dx[i]):
                adx[i] = (adx[i - 1] * (period - 1) + dx[i]) / period

    return adx


def detect_divergence(
    prices: np.ndarray,
    indicator: np.ndarray,
    lookback: int = 20,
) -> dict:
    """
    Detect bullish/bearish divergence between price and an indicator (e.g. RSI, MACD).

    Bullish divergence: price makes lower low, indicator makes higher low → reversal up
    Bearish divergence: price makes higher high, indicator makes lower high → reversal down

    Returns dict with 'type' ('bullish', 'bearish', or 'none') and 'confidence' (0-1).
    """
    if len(prices) < lookback or len(indicator) < lookback:
        return {"type": "none", "confidence": 0.0}

    recent_prices = prices[-lookback:]
    recent_ind = indicator[-lookback:]

    # Remove NaN entries
    valid = ~np.isnan(recent_ind)
    if np.sum(valid) < lookback // 2:
        return {"type": "none", "confidence": 0.0}

    # Split into two halves and compare local extremes
    half = lookback // 2
    first_half_p = recent_prices[:half]
    second_half_p = recent_prices[half:]
    first_half_i = recent_ind[:half]
    second_half_i = recent_ind[half:]

    # Handle NaN in indicator halves
    first_valid = first_half_i[~np.isnan(first_half_i)]
    second_valid = second_half_i[~np.isnan(second_half_i)]
    if len(first_valid) == 0 or len(second_valid) == 0:
        return {"type": "none", "confidence": 0.0}

    # Check for bullish divergence (lower low in price, higher low in indicator)
    price_low1 = np.min(first_half_p)
    price_low2 = np.min(second_half_p)
    ind_low1 = np.min(first_valid)
    ind_low2 = np.min(second_valid)

    if price_low2 < price_low1 and ind_low2 > ind_low1:
        # Confidence based on how pronounced the divergence is
        price_drop = (price_low1 - price_low2) / price_low1 if price_low1 > 0 else 0
        ind_rise = (ind_low2 - ind_low1) / max(abs(ind_low1), 1) if ind_low1 != 0 else 0
        confidence = min(1.0, (price_drop + abs(ind_rise)) * 5)
        return {"type": "bullish", "confidence": round(confidence, 2)}

    # Check for bearish divergence (higher high in price, lower high in indicator)
    price_high1 = np.max(first_half_p)
    price_high2 = np.max(second_half_p)
    ind_high1 = np.max(first_valid)
    ind_high2 = np.max(second_valid)

    if price_high2 > price_high1 and ind_high2 < ind_high1:
        price_rise = (price_high2 - price_high1) / price_high1 if price_high1 > 0 else 0
        ind_drop = (ind_high1 - ind_high2) / max(abs(ind_high1), 1) if ind_high1 != 0 else 0
        confidence = min(1.0, (price_rise + abs(ind_drop)) * 5)
        return {"type": "bearish", "confidence": round(confidence, 2)}

    return {"type": "none", "confidence": 0.0}
