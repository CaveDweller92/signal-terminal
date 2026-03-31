"""
AI Watchlist Builder — Claude picks 12 stocks from the screener's top 30.

Runs daily at 6:00 AM ET, after the screener.
Sends Claude the top 30 with their scores and asks it to curate
a focused 12-stock watchlist with reasoning for each pick.

Falls back to top 12 by composite score if Claude API is unavailable.
"""

import json
from datetime import date

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.screener_result import ScreenerResult
from app.models.watchlist import DailyWatchlist


WATCHLIST_PROMPT = """You are a quantitative swing trading analyst. Given the screener results below, select exactly {size} stocks for the active watchlist.

These picks are for SWING TRADING — positions held for days to weeks, not intraday.

CURRENT MARKET REGIME: {regime}

CURRENTLY HELD POSITIONS (keep these if still strong):
{active_positions}

SCREENER RESULTS (top {count} by composite score):
{screener_data}

For each pick, provide:
1. The stock symbol
2. A 1-2 sentence reasoning explaining WHY this stock is a good swing trade setup

Consider:
- Sector diversification (don't pick 5 tech stocks)
- Multi-day momentum and trend strength based on the regime
- Volume confirmation on daily bars (higher = more conviction)
- Risk/reward balance for multi-day holds
- Keep any currently held positions that still have strong setups
- Favor stocks with clear technical patterns (breakouts, pullbacks to support, oversold bounces)

Respond in JSON format:
{{
  "picks": [
    {{"symbol": "AAPL", "reasoning": "Your reasoning here"}},
    ...
  ]
}}

Return ONLY valid JSON, no other text."""


async def build_watchlist(
    db: AsyncSession,
    regime: str = "unknown",
    watchlist_size: int | None = None,
) -> list[DailyWatchlist]:
    """
    Build today's watchlist from screener results.
    Uses Claude API if available, otherwise falls back to top N.
    """
    today = date.today()
    size = watchlist_size or settings.watchlist_size

    # Get today's screener results
    query = (
        select(ScreenerResult)
        .where(ScreenerResult.scan_date == today)
        .order_by(ScreenerResult.composite_score.desc())
        .limit(30)
    )
    result = await db.execute(query)
    screener_results = list(result.scalars().all())

    if not screener_results:
        return []

    # Get currently held position symbols so Claude can keep them on the watchlist
    from app.models.position import Position
    active_result = await db.execute(
        select(Position.symbol).where(Position.status == "OPEN")
    )
    active_symbols = [row[0] for row in active_result.fetchall()]

    # Clear today's existing watchlist
    await db.execute(
        delete(DailyWatchlist).where(DailyWatchlist.watch_date == today)
    )

    # Try Claude API, fall back to top N
    if settings.has_anthropic_key:
        picks = await _claude_pick(screener_results, regime, size, active_symbols)
    else:
        picks = _fallback_pick(screener_results, size)

    # Deduplicate picks (Claude sometimes returns the same symbol twice)
    seen: set[str] = set()
    unique_picks: list[dict] = []
    for pick in picks:
        sym = pick.get("symbol", "")
        if sym and sym not in seen:
            seen.add(sym)
            unique_picks.append(pick)

    # Save to DB
    watchlist: list[DailyWatchlist] = []
    for i, pick in enumerate(unique_picks):
        sr = next((r for r in screener_results if r.symbol == pick["symbol"]), None)

        entry = DailyWatchlist(
            watch_date=today,
            symbol=pick["symbol"],
            exchange=sr.exchange if sr else None,
            source="ai" if settings.has_anthropic_key else "screener",
            ai_reasoning=pick.get("reasoning"),
            screener_rank=i + 1,
            sector=sr.sector if sr else None,
            regime_at_pick=regime,
        )
        db.add(entry)
        watchlist.append(entry)

    await db.commit()
    return watchlist


async def _claude_pick(
    results: list[ScreenerResult],
    regime: str,
    size: int,
    active_symbols: list[str] | None = None,
) -> list[dict]:
    """Use Claude API to pick stocks from screener results."""
    from anthropic import AsyncAnthropic

    # Format screener data for the prompt
    screener_data = "\n".join(
        f"  {r.symbol} ({r.exchange}) | Composite: {r.composite_score:.2f} | "
        f"Vol: {r.volume_score:.1f} | Momentum: {r.gap_score:.1f} | "
        f"Tech: {r.technical_score:.1f} | Fund: {r.fundamental_score:.1f} | "
        f"News: {r.news_score:.1f} | Sector: {r.sector_score:.1f} | "
        f"RelVol: {r.relative_volume:.1f}x | Sector: {r.sector}"
        for r in results
    )

    active_pos_text = "None" if not active_symbols else ", ".join(active_symbols)

    prompt = WATCHLIST_PROMPT.format(
        size=size,
        regime=regime,
        count=len(results),
        screener_data=screener_data,
        active_positions=active_pos_text,
    )

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    message = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    # Parse response — strip markdown code fences if present
    response_text = message.content[0].text.strip()
    if response_text.startswith("```"):
        response_text = response_text.split("```")[1]
        if response_text.startswith("json"):
            response_text = response_text[4:]
        response_text = response_text.strip()

    try:
        data = json.loads(response_text)
        picks = data.get("picks", [])[:size]
    except json.JSONDecodeError:
        # If Claude doesn't return valid JSON, fall back
        picks = _fallback_pick(results, size)

    # Validate symbols exist in screener results
    valid_symbols = {r.symbol for r in results}
    validated_picks = [p for p in picks if p.get("symbol") in valid_symbols]

    # Fill remaining slots from screener if Claude picked too few
    if len(validated_picks) < size:
        picked_symbols = {p["symbol"] for p in validated_picks}
        for r in results:
            if r.symbol not in picked_symbols:
                validated_picks.append({
                    "symbol": r.symbol,
                    "reasoning": f"Auto-filled from screener (rank {results.index(r) + 1})",
                })
                picked_symbols.add(r.symbol)
            if len(validated_picks) >= size:
                break

    return validated_picks


def _fallback_pick(results: list[ScreenerResult], size: int) -> list[dict]:
    """Fallback: just take the top N by composite score with basic reasoning."""
    picks = []
    sectors_seen: dict[str, int] = {}

    for r in results:
        # Light sector diversification: max 3 per sector
        sector = r.sector or "Unknown"
        if sectors_seen.get(sector, 0) >= 3:
            continue

        sectors_seen[sector] = sectors_seen.get(sector, 0) + 1
        picks.append({
            "symbol": r.symbol,
            "reasoning": (
                f"Screener rank #{len(picks) + 1}. "
                f"Composite {r.composite_score:.2f}, "
                f"relative volume {r.relative_volume:.1f}x. "
                f"Sector: {sector}."
            ),
        })

        if len(picks) >= size:
            break

    return picks
