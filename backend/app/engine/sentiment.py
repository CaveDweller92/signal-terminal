import random
from datetime import datetime

import numpy as np


async def get_sentiment_score(symbol: str) -> dict:
    """
    Returns a simulated sentiment analysis for a stock.

    In production (Phase 3+), this will call a news API and run
    NLP sentiment analysis. For now, generates a plausible score
    from a deterministic seed per symbol + date.

    Score range: -1.0 (extremely negative) to +1.0 (extremely positive)
    """
    today = datetime.utcnow().strftime("%Y%m%d")
    seed = hash(f"sentiment_{symbol}_{today}") % (2**31)
    rng = np.random.default_rng(seed)

    # Base sentiment: slight positive bias (markets trend up long-term)
    base = rng.normal(0.05, 0.35)
    score = float(np.clip(base, -1.0, 1.0))

    # Simulate headline count and impact
    headline_count = int(rng.integers(0, 8))
    positive = int(rng.integers(0, headline_count + 1))
    negative = headline_count - positive

    headlines = []
    sample_positive = [
        f"{symbol} beats earnings expectations",
        f"Analyst upgrades {symbol} to Buy",
        f"{symbol} announces new partnership",
        f"Strong demand drives {symbol} growth",
        f"{symbol} raises full-year guidance",
    ]
    sample_negative = [
        f"{symbol} misses revenue estimates",
        f"Analyst downgrades {symbol} to Hold",
        f"{symbol} faces regulatory scrutiny",
        f"Supply chain issues impact {symbol}",
        f"{symbol} lowers guidance for Q4",
    ]

    rng_stdlib = random.Random(seed)
    for _ in range(min(positive, len(sample_positive))):
        headlines.append({
            "headline": rng_stdlib.choice(sample_positive),
            "impact": round(rng.uniform(0.1, 0.8), 2),
            "category": "positive",
        })
    for _ in range(min(negative, len(sample_negative))):
        headlines.append({
            "headline": rng_stdlib.choice(sample_negative),
            "impact": round(rng.uniform(-0.8, -0.1), 2),
            "category": "negative",
        })

    return {
        "symbol": symbol,
        "score": round(score, 3),
        "headline_count": headline_count,
        "positive_count": positive,
        "negative_count": negative,
        "headlines": headlines,
    }
