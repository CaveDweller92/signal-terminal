"""
Layer 3: Claude Meta-Review.

Runs daily at 4:15 PM ET. Claude reviews the day's performance and
makes high-level recommendations about strategy parameters.

This is the "human in the loop" — Claude can spot patterns that
the Bayesian optimizer misses because it sees the big picture:
- Are we trading too many correlated stocks?
- Is the regime detector lagging?
- Are stop losses consistently too tight in this market?

Falls back to a rule-based summary if Claude API is unavailable.
"""

import json
import logging
from datetime import date, datetime, timedelta

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.meta_review import MetaReview
from app.models.position import Position
from app.models.regime_log import RegimeLog
from app.models.signal import Signal

logger = logging.getLogger(__name__)

REVIEW_PROMPT = """You are a quantitative trading strategy analyst reviewing today's performance for Signal Terminal, a swing trading signals system that holds positions for days to weeks.

## Today's Summary
Date: {date}
Current Regime: {regime}

## Signal Performance
- Signals generated: {total_signals}
- BUY signals: {buy_count}
- SELL signals: {sell_count}

## Trade Performance
- Trades closed today: {trades_closed}
- Winners: {winners} ({win_rate:.1f}% win rate)
- Losers: {losers}
- Average return: {avg_return:+.2f}%
- Best trade: {best_trade}
- Worst trade: {worst_trade}

## Exit Strategy Performance
- Stop loss exits: {stop_loss_count} (avg loss: {stop_loss_avg:.2f}%)
- Profit target exits: {target_count} (avg gain: {target_avg:+.2f}%)
- Indicator reversal exits: {reversal_count}
- Sentiment shift exits: {sentiment_count}
- Manual exits: {manual_count}
- Average days held (winners): {avg_bars_winners:.0f}
- Average days held (losers): {avg_bars_losers:.0f}

## Current Parameters
- ATR stop multiplier: {atr_stop_mult}
- ATR target multiplier: {atr_target_mult}
- Min signal strength: {min_signal_strength}
- RSI bounds: {rsi_oversold}/{rsi_overbought}

## Your Task
Analyze today's performance and provide:
1. A 2-3 sentence summary of how the swing trading strategy performed
2. Specific parameter recommendations (if any)
3. Exit strategy assessment — are stops too tight for multi-day holds? Are targets giving enough room for swing moves?
4. Any concerns about the current regime detection
5. Are we holding through overnight/weekend gaps appropriately?

Respond in JSON:
{{
    "summary": "Your summary here",
    "recommendations": ["rec1", "rec2"],
    "parameter_adjustments": {{"param_name": suggested_value}},
    "exit_strategy_assessment": {{
        "stop_loss_quality": "good/too_tight/too_wide",
        "target_quality": "good/too_conservative/too_aggressive",
        "notes": "Any observations"
    }},
    "regime_assessment": "accurate/lagging/uncertain",
    "risk_level": "low/medium/high"
}}

Return ONLY valid JSON."""


class MetaAnalyst:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_daily_review(self) -> MetaReview:
        """Run the daily meta-review and save results."""
        today = date.today()

        # Gather today's data
        stats = await self._gather_stats(today)

        # Run Claude analysis or fallback
        if settings.has_anthropic_key:
            analysis = await self._claude_review(stats)
        else:
            analysis = self._fallback_review(stats)

        # Save to DB — delete existing record for today first (allow re-runs)
        await self.db.execute(
            delete(MetaReview).where(MetaReview.review_date == today)
        )
        review = MetaReview(
            review_date=today,
            regime_at_review=stats["regime"],
            summary=analysis["summary"],
            recommendations=analysis.get("recommendations"),
            parameter_adjustments=analysis.get("parameter_adjustments"),
            exit_strategy_assessment=analysis.get("exit_strategy_assessment"),
            signals_generated=stats["total_signals"],
            signals_correct=stats["winners"],
            avg_return=stats["avg_return"],
        )
        self.db.add(review)
        await self.db.flush()

        logger.info(f"Daily meta-review completed: {analysis['summary'][:100]}")
        return review

    async def _gather_stats(self, today: date) -> dict:
        """Gather all performance data for today."""
        # Signals today
        sig_result = await self.db.execute(
            select(func.count(Signal.id), Signal.signal_type)
            .where(func.date(Signal.created_at) == today)
            .group_by(Signal.signal_type)
        )
        signal_counts = {row[1]: row[0] for row in sig_result.all()}

        # Closed trades today
        trades_result = await self.db.execute(
            select(Position)
            .where(Position.status == "CLOSED")
            .where(func.date(Position.exit_time) == today)
        )
        trades = list(trades_result.scalars().all())

        winners = [t for t in trades if (t.realized_pnl_pct or 0) > 0]
        losers = [t for t in trades if (t.realized_pnl_pct or 0) <= 0]

        # Exit reason breakdown
        exit_reasons: dict[str, list[Position]] = {}
        for t in trades:
            reason = t.exit_reason or "manual"
            exit_reasons.setdefault(reason, []).append(t)

        def avg_pnl(positions: list) -> float:
            if not positions:
                return 0.0
            return sum(t.realized_pnl_pct or 0 for t in positions) / len(positions)

        def avg_bars(positions: list) -> float:
            if not positions:
                return 0.0
            return sum(t.bars_held or 0 for t in positions) / len(positions)

        # Current regime
        regime_result = await self.db.execute(
            select(RegimeLog).order_by(RegimeLog.created_at.desc()).limit(1)
        )
        regime_log = regime_result.scalar_one_or_none()
        regime = regime_log.regime if regime_log else "unknown"

        return {
            "date": today.isoformat(),
            "regime": regime,
            "total_signals": sum(signal_counts.values()),
            "buy_count": signal_counts.get("BUY", 0),
            "sell_count": signal_counts.get("SELL", 0),
            "trades_closed": len(trades),
            "winners": len(winners),
            "losers": len(losers),
            "win_rate": len(winners) / len(trades) * 100 if trades else 0,
            "avg_return": avg_pnl(trades),
            "best_trade": f"{max((t.realized_pnl_pct or 0) for t in trades):+.2f}% ({max(trades, key=lambda t: t.realized_pnl_pct or 0).symbol})" if trades else "N/A",
            "worst_trade": f"{min((t.realized_pnl_pct or 0) for t in trades):+.2f}% ({min(trades, key=lambda t: t.realized_pnl_pct or 0).symbol})" if trades else "N/A",
            "stop_loss_count": len(exit_reasons.get("stop_loss", [])),
            "stop_loss_avg": abs(avg_pnl(exit_reasons.get("stop_loss", []))),
            "target_count": len(exit_reasons.get("profit_target", [])),
            "target_avg": avg_pnl(exit_reasons.get("profit_target", [])),
            "reversal_count": len(exit_reasons.get("indicator_reversal", [])),
            "sentiment_count": len(exit_reasons.get("sentiment_shift", [])),
            "eod_count": len(exit_reasons.get("eod_warning", [])),
            "manual_count": len(exit_reasons.get("manual", [])),
            "avg_bars_winners": avg_bars(winners),
            "avg_bars_losers": avg_bars(losers),
            "atr_stop_mult": 1.5,  # TODO: read from current config
            "atr_target_mult": 2.5,
            "min_signal_strength": 2.0,
            "rsi_oversold": 30,
            "rsi_overbought": 70,
        }

    async def _claude_review(self, stats: dict) -> dict:
        """Use Claude API for the meta-review."""
        from anthropic import AsyncAnthropic

        prompt = REVIEW_PROMPT.format(**stats)

        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        message = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        try:
            text = message.content[0].text.strip()
            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text.strip())
        except (json.JSONDecodeError, IndexError):
            logger.warning("Claude meta-review returned invalid JSON, using fallback")
            return self._fallback_review(stats)

    def _fallback_review(self, stats: dict) -> dict:
        """Rule-based review when Claude API is unavailable."""
        issues = []
        recommendations = []

        win_rate = stats["win_rate"]
        avg_return = stats["avg_return"]

        # Win rate assessment
        if win_rate < 40:
            issues.append(f"Low win rate ({win_rate:.0f}%)")
            recommendations.append("Consider raising min_signal_strength to filter weak signals")
        elif win_rate > 70:
            issues.append(f"Very high win rate ({win_rate:.0f}%) — targets may be too conservative")
            recommendations.append("Consider widening profit targets")

        # Stop loss assessment
        stop_count = stats["stop_loss_count"]
        total = stats["trades_closed"] or 1
        stop_rate = stop_count / total * 100

        stop_quality = "good"
        if stop_rate > 50:
            stop_quality = "too_tight"
            recommendations.append("Stop losses triggering too often — widen ATR multiplier")
        elif stop_rate < 10 and total > 5:
            stop_quality = "too_wide"

        # Target assessment
        target_quality = "good"
        if stats["avg_bars_winners"] > 50:
            target_quality = "too_aggressive"
            recommendations.append("Winners take too long — tighten profit targets")
        elif stats["avg_bars_winners"] < 5 and stats["target_count"] > 0:
            target_quality = "too_conservative"

        summary = (
            f"{'Good' if avg_return > 0 else 'Difficult'} day with "
            f"{stats['trades_closed']} trades closed. "
            f"Win rate: {win_rate:.0f}%, avg return: {avg_return:+.2f}%. "
            f"{'No major issues.' if not issues else ' '.join(issues)}"
        )

        return {
            "summary": summary,
            "recommendations": recommendations,
            "parameter_adjustments": {},
            "exit_strategy_assessment": {
                "stop_loss_quality": stop_quality,
                "target_quality": target_quality,
                "notes": f"Stop loss exit rate: {stop_rate:.0f}%",
            },
            "regime_assessment": "uncertain" if stats["regime"] == "unknown" else "accurate",
            "risk_level": "high" if avg_return < -1 else "medium" if avg_return < 0 else "low",
        }
