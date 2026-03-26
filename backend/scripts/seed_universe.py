"""Seed the stock universe — run once during cold start."""

import asyncio
import sys
sys.path.insert(0, ".")

from app.db.database import async_session
from app.discovery.universe import seed_universe


async def main():
    async with async_session() as db:
        counts = await seed_universe(db)
        await db.commit()
        total = sum(counts.values())
        print(f"Seeded {total} stocks:")
        for universe, count in counts.items():
            print(f"  {universe}: {count}")


if __name__ == "__main__":
    asyncio.run(main())
