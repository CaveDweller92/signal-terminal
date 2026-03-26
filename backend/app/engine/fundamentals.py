from datetime import datetime

import numpy as np


async def get_fundamental_score(symbol: str) -> dict:
    """
    Returns simulated fundamental analysis for a stock.

    In production (Phase 3+), this pulls real data from financial APIs.
    For now, generates plausible metrics from a deterministic seed.

    Score range: 0.0 (very poor fundamentals) to 5.0 (excellent)
    """
    seed = hash(f"fundamentals_{symbol}") % (2**31)
    rng = np.random.default_rng(seed)

    # Simulate key fundamental metrics
    pe_ratio = float(rng.uniform(8, 60))
    pb_ratio = float(rng.uniform(0.5, 15))
    debt_to_equity = float(rng.uniform(0, 3))
    roe = float(rng.uniform(-5, 40))
    revenue_growth = float(rng.normal(10, 15))
    earnings_growth = float(rng.normal(12, 20))
    profit_margin = float(rng.uniform(2, 35))

    # Scoring: each metric contributes to the overall score
    scores = []

    # P/E: lower is better (but not negative)
    if pe_ratio < 0:
        scores.append(0.5)
    elif pe_ratio < 15:
        scores.append(5.0)
    elif pe_ratio < 25:
        scores.append(3.5)
    elif pe_ratio < 40:
        scores.append(2.0)
    else:
        scores.append(1.0)

    # ROE: higher is better
    if roe > 20:
        scores.append(5.0)
    elif roe > 10:
        scores.append(3.5)
    elif roe > 0:
        scores.append(2.0)
    else:
        scores.append(0.5)

    # Revenue growth: higher is better
    if revenue_growth > 20:
        scores.append(5.0)
    elif revenue_growth > 10:
        scores.append(3.5)
    elif revenue_growth > 0:
        scores.append(2.0)
    else:
        scores.append(1.0)

    # Debt/equity: lower is better
    if debt_to_equity < 0.5:
        scores.append(5.0)
    elif debt_to_equity < 1.0:
        scores.append(3.5)
    elif debt_to_equity < 2.0:
        scores.append(2.0)
    else:
        scores.append(1.0)

    overall = float(np.mean(scores))

    return {
        "symbol": symbol,
        "score": round(overall, 2),
        "pe_ratio": round(pe_ratio, 1),
        "pb_ratio": round(pb_ratio, 1),
        "debt_to_equity": round(debt_to_equity, 2),
        "roe": round(roe, 1),
        "revenue_growth": round(revenue_growth, 1),
        "earnings_growth": round(earnings_growth, 1),
        "profit_margin": round(profit_margin, 1),
    }
