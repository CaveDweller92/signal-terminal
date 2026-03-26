"""
Universe Manager — maintains the master list of tradable stocks.

Seeds S&P 500, NASDAQ 100, and TSX stocks into the stock_universe table.
Phase 1 uses a hardcoded representative subset (~120 stocks).
Production would pull from Wikipedia lists or a data API.
"""

from datetime import datetime

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock_universe import StockUniverse

# Representative subset of S&P 500 stocks (top by market cap + sector diversity)
SP500_STOCKS = [
    ("AAPL", "Apple Inc.", "Technology", "Consumer Electronics"),
    ("MSFT", "Microsoft Corporation", "Technology", "Software"),
    ("GOOGL", "Alphabet Inc.", "Technology", "Internet Services"),
    ("AMZN", "Amazon.com Inc.", "Consumer Cyclical", "Internet Retail"),
    ("NVDA", "NVIDIA Corporation", "Technology", "Semiconductors"),
    ("META", "Meta Platforms Inc.", "Technology", "Internet Services"),
    ("TSLA", "Tesla Inc.", "Consumer Cyclical", "Auto Manufacturers"),
    ("BRK.B", "Berkshire Hathaway Inc.", "Financial Services", "Insurance"),
    ("JPM", "JPMorgan Chase & Co.", "Financial Services", "Banks"),
    ("V", "Visa Inc.", "Financial Services", "Credit Services"),
    ("UNH", "UnitedHealth Group Inc.", "Healthcare", "Healthcare Plans"),
    ("JNJ", "Johnson & Johnson", "Healthcare", "Drug Manufacturers"),
    ("XOM", "Exxon Mobil Corporation", "Energy", "Oil & Gas"),
    ("WMT", "Walmart Inc.", "Consumer Defensive", "Discount Stores"),
    ("PG", "Procter & Gamble Co.", "Consumer Defensive", "Household Products"),
    ("MA", "Mastercard Inc.", "Financial Services", "Credit Services"),
    ("HD", "Home Depot Inc.", "Consumer Cyclical", "Home Improvement"),
    ("CVX", "Chevron Corporation", "Energy", "Oil & Gas"),
    ("LLY", "Eli Lilly and Company", "Healthcare", "Drug Manufacturers"),
    ("ABBV", "AbbVie Inc.", "Healthcare", "Drug Manufacturers"),
    ("PFE", "Pfizer Inc.", "Healthcare", "Drug Manufacturers"),
    ("MRK", "Merck & Co. Inc.", "Healthcare", "Drug Manufacturers"),
    ("COST", "Costco Wholesale", "Consumer Defensive", "Discount Stores"),
    ("AVGO", "Broadcom Inc.", "Technology", "Semiconductors"),
    ("PEP", "PepsiCo Inc.", "Consumer Defensive", "Beverages"),
    ("KO", "Coca-Cola Company", "Consumer Defensive", "Beverages"),
    ("TMO", "Thermo Fisher Scientific", "Healthcare", "Diagnostics"),
    ("CSCO", "Cisco Systems Inc.", "Technology", "Networking"),
    ("CRM", "Salesforce Inc.", "Technology", "Software"),
    ("ACN", "Accenture plc", "Technology", "IT Services"),
    ("ABT", "Abbott Laboratories", "Healthcare", "Medical Devices"),
    ("MCD", "McDonald's Corporation", "Consumer Cyclical", "Restaurants"),
    ("NKE", "Nike Inc.", "Consumer Cyclical", "Footwear"),
    ("DIS", "Walt Disney Company", "Communication Services", "Entertainment"),
    ("AMD", "Advanced Micro Devices", "Technology", "Semiconductors"),
    ("NFLX", "Netflix Inc.", "Communication Services", "Entertainment"),
    ("INTC", "Intel Corporation", "Technology", "Semiconductors"),
    ("PYPL", "PayPal Holdings Inc.", "Financial Services", "Credit Services"),
    ("BA", "Boeing Company", "Industrials", "Aerospace"),
    ("GS", "Goldman Sachs Group", "Financial Services", "Banks"),
    ("CAT", "Caterpillar Inc.", "Industrials", "Farm & Construction"),
    ("RTX", "RTX Corporation", "Industrials", "Aerospace"),
    ("SPGI", "S&P Global Inc.", "Financial Services", "Financial Data"),
    ("LOW", "Lowe's Companies", "Consumer Cyclical", "Home Improvement"),
    ("DE", "Deere & Company", "Industrials", "Farm & Construction"),
    ("SYK", "Stryker Corporation", "Healthcare", "Medical Devices"),
    ("ADP", "Automatic Data Processing", "Industrials", "Staffing"),
    ("MMM", "3M Company", "Industrials", "Conglomerates"),
    ("ISRG", "Intuitive Surgical", "Healthcare", "Medical Devices"),
    ("GILD", "Gilead Sciences Inc.", "Healthcare", "Biotechnology"),
]

# NASDAQ 100 additions (not already in SP500 list)
NASDAQ100_STOCKS = [
    ("MRVL", "Marvell Technology", "Technology", "Semiconductors"),
    ("PANW", "Palo Alto Networks", "Technology", "Cybersecurity"),
    ("SNPS", "Synopsys Inc.", "Technology", "Software"),
    ("CDNS", "Cadence Design Systems", "Technology", "Software"),
    ("KLAC", "KLA Corporation", "Technology", "Semiconductors"),
    ("LRCX", "Lam Research", "Technology", "Semiconductors"),
    ("ADBE", "Adobe Inc.", "Technology", "Software"),
    ("MELI", "MercadoLibre Inc.", "Consumer Cyclical", "Internet Retail"),
    ("FTNT", "Fortinet Inc.", "Technology", "Cybersecurity"),
    ("WDAY", "Workday Inc.", "Technology", "Software"),
    ("DXCM", "DexCom Inc.", "Healthcare", "Medical Devices"),
    ("TEAM", "Atlassian Corporation", "Technology", "Software"),
    ("ZS", "Zscaler Inc.", "Technology", "Cybersecurity"),
    ("CRWD", "CrowdStrike Holdings", "Technology", "Cybersecurity"),
    ("MNST", "Monster Beverage", "Consumer Defensive", "Beverages"),
    ("ODFL", "Old Dominion Freight Line", "Industrials", "Trucking"),
    ("FAST", "Fastenal Company", "Industrials", "Industrial Distribution"),
    ("TTD", "Trade Desk Inc.", "Technology", "Software"),
    ("CPRT", "Copart Inc.", "Industrials", "Auto Parts"),
    ("SMCI", "Super Micro Computer", "Technology", "Computer Hardware"),
    ("ON", "ON Semiconductor", "Technology", "Semiconductors"),
    ("DASH", "DoorDash Inc.", "Technology", "Internet Services"),
    ("COIN", "Coinbase Global", "Financial Services", "Capital Markets"),
    ("MCHP", "Microchip Technology", "Technology", "Semiconductors"),
    ("ARM", "Arm Holdings plc", "Technology", "Semiconductors"),
]

# TSX stocks (Canadian market)
TSX_STOCKS = [
    ("RY", "Royal Bank of Canada", "Financial Services", "Banks"),
    ("TD", "Toronto-Dominion Bank", "Financial Services", "Banks"),
    ("BNS", "Bank of Nova Scotia", "Financial Services", "Banks"),
    ("BMO", "Bank of Montreal", "Financial Services", "Banks"),
    ("CM", "Canadian Imperial Bank", "Financial Services", "Banks"),
    ("ENB", "Enbridge Inc.", "Energy", "Oil & Gas Midstream"),
    ("CNR", "Canadian National Railway", "Industrials", "Railroads"),
    ("CP", "Canadian Pacific Kansas City", "Industrials", "Railroads"),
    ("SHOP", "Shopify Inc.", "Technology", "Software"),
    ("BCE", "BCE Inc.", "Communication Services", "Telecom"),
    ("TRP", "TC Energy Corporation", "Energy", "Oil & Gas Midstream"),
    ("SU", "Suncor Energy Inc.", "Energy", "Oil & Gas"),
    ("CNQ", "Canadian Natural Resources", "Energy", "Oil & Gas"),
    ("MFC", "Manulife Financial", "Financial Services", "Insurance"),
    ("ABX", "Barrick Gold Corporation", "Materials", "Gold"),
    ("ATD", "Alimentation Couche-Tard", "Consumer Defensive", "Grocery"),
    ("WCN", "Waste Connections Inc.", "Industrials", "Waste Management"),
    ("FTS", "Fortis Inc.", "Utilities", "Utilities"),
    ("L", "Loblaw Companies", "Consumer Defensive", "Grocery"),
    ("MG", "Magna International", "Consumer Cyclical", "Auto Parts"),
]


async def seed_universe(db: AsyncSession) -> dict:
    """
    Seed the stock_universe table with all tracked stocks.
    Clears existing data and re-inserts (idempotent).
    Returns count per universe.
    """
    # Clear existing
    await db.execute(delete(StockUniverse))

    counts = {"sp500": 0, "nasdaq100": 0, "tsx": 0}

    for symbol, name, sector, industry in SP500_STOCKS:
        db.add(StockUniverse(
            symbol=symbol, name=name, exchange="NYSE",
            universe="sp500", sector=sector, industry=industry,
            country="US", currency="USD",
        ))
        counts["sp500"] += 1

    for symbol, name, sector, industry in NASDAQ100_STOCKS:
        db.add(StockUniverse(
            symbol=symbol, name=name, exchange="NASDAQ",
            universe="nasdaq100", sector=sector, industry=industry,
            country="US", currency="USD",
        ))
        counts["nasdaq100"] += 1

    for symbol, name, sector, industry in TSX_STOCKS:
        db.add(StockUniverse(
            symbol=symbol, name=name, exchange="TSX",
            universe="tsx", sector=sector, industry=industry,
            country="CA", currency="CAD",
        ))
        counts["tsx"] += 1

    await db.commit()
    return counts


async def get_active_symbols(db: AsyncSession, universe: str | None = None) -> list[StockUniverse]:
    """Get all active stocks, optionally filtered by universe."""
    query = select(StockUniverse).where(StockUniverse.is_active == True)
    if universe:
        query = query.where(StockUniverse.universe == universe)
    result = await db.execute(query)
    return list(result.scalars().all())
