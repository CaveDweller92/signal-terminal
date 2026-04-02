"""
Signal Persistence Service — wraps SignalAnalyzer and persists results to DB.

This closes the feedback loop: signals are now stored in the signals table,
enabling outcome tracking, performance measurement, and adaptive learning.

Deduplication: one signal per symbol per day (query + update/insert).
"""

import logging
from datetime import date, datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.analyzer import AnalyzerConfig, SignalAnalyzer
from app.engine.data_provider import DataProvider
from app.models.parameter_snapshot import ParameterSnapshot
from app.models.regime_log import RegimeLog
from app.models.signal import Signal

logger = logging.getLogger(__name__)


class SignalService:
    """Analyze + persist signals in one step."""

    def __init__(self, db: AsyncSession, data_provider: DataProvider):
        self.db = db
        self.data = data_provider
        self._analyzer: SignalAnalyzer | None = None

    async def _get_analyzer(self) -> SignalAnalyzer:
        """Create analyzer with regime-tuned parameters from latest snapshot."""
        if self._analyzer is None:
            snapshot = await self._get_latest_snapshot()
            overrides = snapshot.full_config if snapshot else None
            config = AnalyzerConfig(overrides=overrides)
            self._analyzer = SignalAnalyzer(self.data, config)
        return self._analyzer

    async def analyze_and_persist(self, symbol: str) -> dict | None:
        """
        Run analysis on a symbol, persist to DB, return the signal dict
        with the DB record's `id` attached.

        Deduplicates: one signal per symbol per calendar day.
        """
        analyzer = await self._get_analyzer()
        result = await analyzer.analyze(symbol)
        if result is None:
            return None

        regime = await self._get_current_regime()
        snapshot_id = await self._get_latest_snapshot_id()
        today = date.today()

        # Check for existing signal for this symbol today
        existing = await self.db.execute(
            select(Signal)
            .where(Signal.symbol == symbol)
            .where(func.date(Signal.created_at) == today)
            .limit(1)
        )
        signal_obj = existing.scalar_one_or_none()

        if signal_obj:
            # Update existing
            signal_obj.signal_type = result["signal_type"]
            signal_obj.conviction = result["conviction"]
            signal_obj.tech_score = result["tech_score"]
            signal_obj.sentiment_score = result["sentiment_score"]
            signal_obj.fundamental_score = result["fundamental_score"]
            signal_obj.price_at_signal = result["price_at_signal"]
            signal_obj.suggested_stop_loss = result["suggested_stop_loss"]
            signal_obj.suggested_profit_target = result["suggested_profit_target"]
            signal_obj.atr_at_signal = result["atr_at_signal"]
            signal_obj.reasons = result["reasons"]
            signal_obj.regime_at_signal = regime
            signal_obj.config_snapshot_id = snapshot_id
        else:
            # Insert new
            signal_obj = Signal(
                symbol=result["symbol"],
                signal_type=result["signal_type"],
                conviction=result["conviction"],
                tech_score=result["tech_score"],
                sentiment_score=result["sentiment_score"],
                fundamental_score=result["fundamental_score"],
                price_at_signal=result["price_at_signal"],
                suggested_stop_loss=result["suggested_stop_loss"],
                suggested_profit_target=result["suggested_profit_target"],
                atr_at_signal=result["atr_at_signal"],
                reasons=result["reasons"],
                regime_at_signal=regime,
                config_snapshot_id=snapshot_id,
            )
            self.db.add(signal_obj)

        await self.db.flush()
        if not signal_obj.id:
            await self.db.refresh(signal_obj)

        # Attach DB id to the result dict (backward-compatible)
        result["id"] = signal_obj.id
        result["regime_at_signal"] = regime

        return result

    async def analyze_batch(self, symbols: list[str]) -> list[dict]:
        """Analyze and persist a batch of symbols. Returns list of signal dicts."""
        results = []
        for symbol in symbols:
            try:
                signal = await self.analyze_and_persist(symbol)
                if signal is not None:
                    results.append(signal)
            except Exception as e:
                logger.error(f"SignalService: error analyzing {symbol}: {e}")
        return results

    async def get_todays_signal(self, symbol: str) -> Signal | None:
        """Get today's persisted signal for a symbol (if any)."""
        today = date.today()
        result = await self.db.execute(
            select(Signal)
            .where(Signal.symbol == symbol)
            .where(func.date(Signal.created_at) == today)
            .order_by(Signal.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_current_regime(self) -> str | None:
        result = await self.db.execute(
            select(RegimeLog.regime)
            .order_by(RegimeLog.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_latest_snapshot(self) -> ParameterSnapshot | None:
        result = await self.db.execute(
            select(ParameterSnapshot)
            .order_by(ParameterSnapshot.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_latest_snapshot_id(self) -> int | None:
        snapshot = await self._get_latest_snapshot()
        return snapshot.id if snapshot else None
