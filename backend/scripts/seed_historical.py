"""Seed historical simulated data — generates signals for backtesting."""

import asyncio
import sys
sys.path.insert(0, ".")

from datetime import datetime
from app.db.database import async_session
from app.engine.data_provider import SimulatedDataProvider
from app.engine.analyzer import SignalAnalyzer
from app.models.signal import Signal


SYMBOLS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META",
    "TSLA", "AMD", "NFLX", "JPM", "V", "HD",
]


async def main():
    provider = SimulatedDataProvider()
    analyzer = SignalAnalyzer(provider)

    async with async_session() as db:
        count = 0
        for symbol in SYMBOLS:
            result = await analyzer.analyze(symbol)
            signal = Signal(
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
            )
            db.add(signal)
            count += 1

        await db.commit()
        print(f"Seeded {count} historical signals for {len(SYMBOLS)} symbols")


if __name__ == "__main__":
    asyncio.run(main())
