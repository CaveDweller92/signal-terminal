"""
Universe Manager — maintains the master list of tradable stocks.

US stocks:
  - Fetched from Finnhub (/stock/symbol?exchange=US) when API key is set
  - Falls back to hardcoded ~60 stocks otherwise

TSX 60:
  - Fetched dynamically from Wikipedia (S&P/TSX 60 page) via pandas.read_html
  - Falls back to hardcoded list if Wikipedia is unreachable
"""

import io
import logging
from datetime import datetime

import httpx
import pandas as pd
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.stock_universe import StockUniverse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hardcoded fallback lists (used when no Finnhub key is available)
# ---------------------------------------------------------------------------

SP500_STOCKS = [
    ("AAPL", "Apple Inc.", "NYSE", "sp500", "Technology", "Consumer Electronics", "US", "USD"),
    ("MSFT", "Microsoft Corporation", "NYSE", "sp500", "Technology", "Software", "US", "USD"),
    ("GOOGL", "Alphabet Inc.", "NASDAQ", "sp500", "Technology", "Internet Services", "US", "USD"),
    ("AMZN", "Amazon.com Inc.", "NASDAQ", "sp500", "Consumer Cyclical", "Internet Retail", "US", "USD"),
    ("NVDA", "NVIDIA Corporation", "NASDAQ", "sp500", "Technology", "Semiconductors", "US", "USD"),
    ("META", "Meta Platforms Inc.", "NASDAQ", "sp500", "Technology", "Internet Services", "US", "USD"),
    ("TSLA", "Tesla Inc.", "NASDAQ", "sp500", "Consumer Cyclical", "Auto Manufacturers", "US", "USD"),
    ("BRK.B", "Berkshire Hathaway Inc.", "NYSE", "sp500", "Financial Services", "Insurance", "US", "USD"),
    ("JPM", "JPMorgan Chase & Co.", "NYSE", "sp500", "Financial Services", "Banks", "US", "USD"),
    ("V", "Visa Inc.", "NYSE", "sp500", "Financial Services", "Credit Services", "US", "USD"),
    ("UNH", "UnitedHealth Group Inc.", "NYSE", "sp500", "Healthcare", "Healthcare Plans", "US", "USD"),
    ("JNJ", "Johnson & Johnson", "NYSE", "sp500", "Healthcare", "Drug Manufacturers", "US", "USD"),
    ("XOM", "Exxon Mobil Corporation", "NYSE", "sp500", "Energy", "Oil & Gas", "US", "USD"),
    ("WMT", "Walmart Inc.", "NYSE", "sp500", "Consumer Defensive", "Discount Stores", "US", "USD"),
    ("PG", "Procter & Gamble Co.", "NYSE", "sp500", "Consumer Defensive", "Household Products", "US", "USD"),
    ("MA", "Mastercard Inc.", "NYSE", "sp500", "Financial Services", "Credit Services", "US", "USD"),
    ("HD", "Home Depot Inc.", "NYSE", "sp500", "Consumer Cyclical", "Home Improvement", "US", "USD"),
    ("CVX", "Chevron Corporation", "NYSE", "sp500", "Energy", "Oil & Gas", "US", "USD"),
    ("LLY", "Eli Lilly and Company", "NYSE", "sp500", "Healthcare", "Drug Manufacturers", "US", "USD"),
    ("ABBV", "AbbVie Inc.", "NYSE", "sp500", "Healthcare", "Drug Manufacturers", "US", "USD"),
    ("PFE", "Pfizer Inc.", "NYSE", "sp500", "Healthcare", "Drug Manufacturers", "US", "USD"),
    ("MRK", "Merck & Co. Inc.", "NYSE", "sp500", "Healthcare", "Drug Manufacturers", "US", "USD"),
    ("COST", "Costco Wholesale", "NASDAQ", "sp500", "Consumer Defensive", "Discount Stores", "US", "USD"),
    ("AVGO", "Broadcom Inc.", "NASDAQ", "sp500", "Technology", "Semiconductors", "US", "USD"),
    ("PEP", "PepsiCo Inc.", "NASDAQ", "sp500", "Consumer Defensive", "Beverages", "US", "USD"),
    ("KO", "Coca-Cola Company", "NYSE", "sp500", "Consumer Defensive", "Beverages", "US", "USD"),
    ("TMO", "Thermo Fisher Scientific", "NYSE", "sp500", "Healthcare", "Diagnostics", "US", "USD"),
    ("CSCO", "Cisco Systems Inc.", "NASDAQ", "sp500", "Technology", "Networking", "US", "USD"),
    ("CRM", "Salesforce Inc.", "NYSE", "sp500", "Technology", "Software", "US", "USD"),
    ("ACN", "Accenture plc", "NYSE", "sp500", "Technology", "IT Services", "US", "USD"),
    ("ABT", "Abbott Laboratories", "NYSE", "sp500", "Healthcare", "Medical Devices", "US", "USD"),
    ("MCD", "McDonald's Corporation", "NYSE", "sp500", "Consumer Cyclical", "Restaurants", "US", "USD"),
    ("NKE", "Nike Inc.", "NYSE", "sp500", "Consumer Cyclical", "Footwear", "US", "USD"),
    ("DIS", "Walt Disney Company", "NYSE", "sp500", "Communication Services", "Entertainment", "US", "USD"),
    ("AMD", "Advanced Micro Devices", "NASDAQ", "sp500", "Technology", "Semiconductors", "US", "USD"),
    ("NFLX", "Netflix Inc.", "NASDAQ", "sp500", "Communication Services", "Entertainment", "US", "USD"),
    ("INTC", "Intel Corporation", "NASDAQ", "sp500", "Technology", "Semiconductors", "US", "USD"),
    ("PYPL", "PayPal Holdings Inc.", "NASDAQ", "sp500", "Financial Services", "Credit Services", "US", "USD"),
    ("BA", "Boeing Company", "NYSE", "sp500", "Industrials", "Aerospace", "US", "USD"),
    ("GS", "Goldman Sachs Group", "NYSE", "sp500", "Financial Services", "Banks", "US", "USD"),
    ("CAT", "Caterpillar Inc.", "NYSE", "sp500", "Industrials", "Farm & Construction", "US", "USD"),
    ("RTX", "RTX Corporation", "NYSE", "sp500", "Industrials", "Aerospace", "US", "USD"),
    ("SPGI", "S&P Global Inc.", "NYSE", "sp500", "Financial Services", "Financial Data", "US", "USD"),
    ("LOW", "Lowe's Companies", "NYSE", "sp500", "Consumer Cyclical", "Home Improvement", "US", "USD"),
    ("DE", "Deere & Company", "NYSE", "sp500", "Industrials", "Farm & Construction", "US", "USD"),
    ("SYK", "Stryker Corporation", "NYSE", "sp500", "Healthcare", "Medical Devices", "US", "USD"),
    ("ADP", "Automatic Data Processing", "NASDAQ", "sp500", "Industrials", "Staffing", "US", "USD"),
    ("ISRG", "Intuitive Surgical", "NASDAQ", "sp500", "Healthcare", "Medical Devices", "US", "USD"),
    ("GILD", "Gilead Sciences Inc.", "NASDAQ", "sp500", "Healthcare", "Biotechnology", "US", "USD"),
]

NASDAQ100_STOCKS = [
    ("MRVL", "Marvell Technology", "NASDAQ", "nasdaq100", "Technology", "Semiconductors", "US", "USD"),
    ("PANW", "Palo Alto Networks", "NASDAQ", "nasdaq100", "Technology", "Cybersecurity", "US", "USD"),
    ("ADBE", "Adobe Inc.", "NASDAQ", "nasdaq100", "Technology", "Software", "US", "USD"),
    ("CRWD", "CrowdStrike Holdings", "NASDAQ", "nasdaq100", "Technology", "Cybersecurity", "US", "USD"),
    ("TEAM", "Atlassian Corporation", "NASDAQ", "nasdaq100", "Technology", "Software", "US", "USD"),
    ("FTNT", "Fortinet Inc.", "NASDAQ", "nasdaq100", "Technology", "Cybersecurity", "US", "USD"),
    ("ZS", "Zscaler Inc.", "NASDAQ", "nasdaq100", "Technology", "Cybersecurity", "US", "USD"),
    ("WDAY", "Workday Inc.", "NASDAQ", "nasdaq100", "Technology", "Software", "US", "USD"),
    ("TTD", "Trade Desk Inc.", "NASDAQ", "nasdaq100", "Technology", "Software", "US", "USD"),
    ("COIN", "Coinbase Global", "NASDAQ", "nasdaq100", "Financial Services", "Capital Markets", "US", "USD"),
    ("DASH", "DoorDash Inc.", "NASDAQ", "nasdaq100", "Technology", "Internet Services", "US", "USD"),
    ("ARM", "Arm Holdings plc", "NASDAQ", "nasdaq100", "Technology", "Semiconductors", "US", "USD"),
]

# Fallback TSX list — used only if Wikipedia is unreachable
TSX_STOCKS_FALLBACK = [
    ("RY.TO",   "Royal Bank of Canada",        "TSX", "tsx", "Financial Services",     "Banks",               "CA", "CAD"),
    ("TD.TO",   "Toronto-Dominion Bank",        "TSX", "tsx", "Financial Services",     "Banks",               "CA", "CAD"),
    ("BNS.TO",  "Bank of Nova Scotia",          "TSX", "tsx", "Financial Services",     "Banks",               "CA", "CAD"),
    ("BMO.TO",  "Bank of Montreal",             "TSX", "tsx", "Financial Services",     "Banks",               "CA", "CAD"),
    ("CM.TO",   "Canadian Imperial Bank",       "TSX", "tsx", "Financial Services",     "Banks",               "CA", "CAD"),
    ("ENB.TO",  "Enbridge Inc.",                "TSX", "tsx", "Energy",                 "Oil & Gas Midstream", "CA", "CAD"),
    ("CNR.TO",  "Canadian National Railway",    "TSX", "tsx", "Industrials",            "Railroads",           "CA", "CAD"),
    ("CP.TO",   "Canadian Pacific Kansas City", "TSX", "tsx", "Industrials",            "Railroads",           "CA", "CAD"),
    ("SHOP.TO", "Shopify Inc.",                 "TSX", "tsx", "Technology",             "Software",            "CA", "CAD"),
    ("BCE.TO",  "BCE Inc.",                     "TSX", "tsx", "Communication Services", "Telecom",             "CA", "CAD"),
    ("TRP.TO",  "TC Energy Corporation",        "TSX", "tsx", "Energy",                 "Oil & Gas Midstream", "CA", "CAD"),
    ("SU.TO",   "Suncor Energy Inc.",           "TSX", "tsx", "Energy",                 "Oil & Gas",           "CA", "CAD"),
    ("CNQ.TO",  "Canadian Natural Resources",   "TSX", "tsx", "Energy",                 "Oil & Gas",           "CA", "CAD"),
    ("MFC.TO",  "Manulife Financial",           "TSX", "tsx", "Financial Services",     "Insurance",           "CA", "CAD"),
    ("ABX.TO",  "Barrick Gold Corporation",     "TSX", "tsx", "Materials",              "Gold",                "CA", "CAD"),
    ("ATD.TO",  "Alimentation Couche-Tard",     "TSX", "tsx", "Consumer Defensive",     "Grocery",             "CA", "CAD"),
    ("WCN.TO",  "Waste Connections Inc.",       "TSX", "tsx", "Industrials",            "Waste Management",    "CA", "CAD"),
    ("FTS.TO",  "Fortis Inc.",                  "TSX", "tsx", "Utilities",              "Utilities",           "CA", "CAD"),
    ("L.TO",    "Loblaw Companies",             "TSX", "tsx", "Consumer Defensive",     "Grocery",             "CA", "CAD"),
    ("MG.TO",   "Magna International",          "TSX", "tsx", "Consumer Cyclical",      "Auto Parts",          "CA", "CAD"),
]


# ---------------------------------------------------------------------------
# Finnhub fetcher
# ---------------------------------------------------------------------------

async def _fetch_finnhub_symbols(exchange: str, api_key: str) -> list[dict]:
    """
    Fetch all common stocks for an exchange from Finnhub.

    exchange: "US" for NYSE/NASDAQ
    Returns list of {symbol, description, type} dicts.
    Follows redirects (Finnhub returns 302 to a static CDN file).
    """
    url = f"https://finnhub.io/api/v1/stock/symbol?exchange={exchange}&token={api_key}"
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
        # Filter to common stocks only — exclude ETFs, warrants, rights, etc.
        return [
            s for s in data
            if s.get("type") in ("Common Stock", "EQS")
        ]
    except Exception as e:
        logger.error(f"Finnhub symbol fetch failed for exchange={exchange}: {e}")
        return []


async def _fetch_tsx60_from_wiki() -> list[tuple]:
    """
    Fetch the S&P/TSX 60 constituent list from Wikipedia.
    Returns list of (symbol_with_TO, name) tuples.
    Falls back to TSX_STOCKS_FALLBACK if Wikipedia is unreachable.
    """
    url = "https://en.wikipedia.org/wiki/S%26P/TSX_60"
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; signal-terminal/1.0)"}
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers=headers) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            html = resp.text

        tables = pd.read_html(io.StringIO(html), flavor="lxml")
        # Find the table that has a ticker/symbol column
        df = None
        for t in tables:
            cols = [str(c).lower() for c in t.columns]
            if any("ticker" in c or "symbol" in c for c in cols):
                df = t
                break

        if df is None:
            logger.warning("TSX 60 Wikipedia: could not find ticker table, using fallback")
            return TSX_STOCKS_FALLBACK

        # Normalise column names
        df.columns = [str(c).lower().strip() for c in df.columns]
        ticker_col = next(c for c in df.columns if "ticker" in c or "symbol" in c)
        name_col = next((c for c in df.columns if "company" in c or "name" in c), None)

        results = []
        for _, row in df.iterrows():
            symbol = str(row[ticker_col]).strip()
            name = str(row[name_col]).strip() if name_col else symbol
            if not symbol or symbol == "nan":
                continue
            if not symbol.endswith(".TO"):
                symbol = f"{symbol}.TO"
            results.append((symbol, name))

        logger.info(f"Wikipedia TSX 60: fetched {len(results)} symbols")
        return results

    except Exception as e:
        logger.warning(f"TSX 60 Wikipedia fetch failed ({e}), using fallback list")
        return TSX_STOCKS_FALLBACK


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def seed_universe(db: AsyncSession) -> dict:
    """
    Seed the stock_universe table.

    If FINNHUB_API_KEY is set and USE_SIMULATED_DATA=false:
      → fetches real symbol lists from Finnhub (full US + TSX universes)
    Otherwise:
      → falls back to the hardcoded representative subset
    """
    await db.execute(delete(StockUniverse))

    use_finnhub = (
        not settings.use_simulated_data
        and bool(settings.finnhub_api_key)
    )

    if use_finnhub:
        return await _seed_from_finnhub(db)
    else:
        return await _seed_from_hardcoded(db)


async def _seed_from_finnhub(db: AsyncSession) -> dict:
    logger.info("Seeding universe from Finnhub (US) + hardcoded TSX...")
    counts = {"us": 0, "tsx": 0}

    # US stocks — Finnhub free tier supports exchange=US
    us_symbols = await _fetch_finnhub_symbols("US", settings.finnhub_api_key)
    logger.info(f"Finnhub returned {len(us_symbols)} US common stocks")

    for s in us_symbols:
        db.add(StockUniverse(
            symbol=s["symbol"][:10],
            name=(s.get("description") or s["symbol"])[:200],
            exchange=s.get("mic", "US")[:20],
            universe="sp500",
            country="US",
            currency="USD",
            last_updated=datetime.utcnow(),
        ))
        counts["us"] += 1

    # TSX — fetch from Wikipedia (exchange=TO requires Finnhub paid plan)
    tsx_wiki = await _fetch_tsx60_from_wiki()
    for item in tsx_wiki:
        if isinstance(item, tuple) and len(item) == 8:
            # fallback tuple format
            symbol, name, exchange, universe, sector, industry, country, currency = item
        else:
            # wiki format: (symbol, name)
            symbol, name = item
            exchange, universe, sector, industry, country, currency = "TSX", "tsx", None, None, "CA", "CAD"
        db.add(StockUniverse(
            symbol=symbol[:10], name=name[:200], exchange=exchange, universe=universe,
            sector=sector, industry=industry, country=country, currency=currency,
            last_updated=datetime.utcnow(),
        ))
        counts["tsx"] += 1

    await db.commit()
    return counts


async def _seed_from_hardcoded(db: AsyncSession) -> dict:
    logger.info("Seeding universe from hardcoded fallback list...")
    counts = {"sp500": 0, "nasdaq100": 0, "tsx": 0}

    all_stocks = (
        [(s, "sp500") for s in SP500_STOCKS]
        + [(s, "nasdaq100") for s in NASDAQ100_STOCKS]
        + [(s, "tsx") for s in TSX_STOCKS_FALLBACK]
    )

    for stock, _ in all_stocks:
        symbol, name, exchange, universe, sector, industry, country, currency = stock
        db.add(StockUniverse(
            symbol=symbol, name=name, exchange=exchange, universe=universe,
            sector=sector, industry=industry, country=country, currency=currency,
            last_updated=datetime.utcnow(),
        ))
        counts[universe] += 1

    await db.commit()
    return counts


async def get_active_symbols(db: AsyncSession, universe: str | None = None) -> list[StockUniverse]:
    """Get all active stocks, optionally filtered by universe."""
    query = select(StockUniverse).where(StockUniverse.is_active == True)
    if universe:
        query = query.where(StockUniverse.universe == universe)
    result = await db.execute(query)
    return list(result.scalars().all())
