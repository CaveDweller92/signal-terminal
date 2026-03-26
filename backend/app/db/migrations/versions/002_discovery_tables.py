"""Add stock_universe, screener_results, daily_watchlist tables

Revision ID: 002
Revises: 001
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stock_universe",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(10), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("exchange", sa.String(20), nullable=False),
        sa.Column("universe", sa.String(20), nullable=False),
        sa.Column("sector", sa.String(50), nullable=True),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("market_cap", sa.BigInteger(), nullable=True),
        sa.Column("avg_volume_30d", sa.BigInteger(), nullable=True),
        sa.Column("country", sa.String(5), server_default="US"),
        sa.Column("currency", sa.String(3), server_default="USD"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("last_updated", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("symbol", "exchange"),
    )
    op.create_index("ix_stock_universe_symbol", "stock_universe", ["symbol"])
    op.create_index("ix_stock_universe_universe", "stock_universe", ["universe"])

    op.create_table(
        "screener_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scan_date", sa.Date(), nullable=False),
        sa.Column("symbol", sa.String(10), nullable=False),
        sa.Column("exchange", sa.String(20), nullable=True),
        sa.Column("composite_score", sa.Float(), nullable=False),
        sa.Column("volume_score", sa.Float(), nullable=True),
        sa.Column("gap_score", sa.Float(), nullable=True),
        sa.Column("technical_score", sa.Float(), nullable=True),
        sa.Column("fundamental_score", sa.Float(), nullable=True),
        sa.Column("news_score", sa.Float(), nullable=True),
        sa.Column("sector_score", sa.Float(), nullable=True),
        sa.Column("premarket_gap_pct", sa.Float(), nullable=True),
        sa.Column("relative_volume", sa.Float(), nullable=True),
        sa.Column("sector", sa.String(50), nullable=True),
        sa.Column("has_catalyst", sa.Boolean(), server_default="false"),
        sa.Column("catalyst_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("scan_date", "symbol"),
    )
    op.create_index("ix_screener_results_symbol", "screener_results", ["symbol"])
    op.create_index("ix_screener_results_scan_date", "screener_results", ["scan_date"])

    op.create_table(
        "daily_watchlist",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("watch_date", sa.Date(), nullable=False),
        sa.Column("symbol", sa.String(10), nullable=False),
        sa.Column("exchange", sa.String(20), nullable=True),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("ai_reasoning", sa.Text(), nullable=True),
        sa.Column("screener_rank", sa.Integer(), nullable=True),
        sa.Column("sector", sa.String(50), nullable=True),
        sa.Column("regime_at_pick", sa.String(30), nullable=True),
        sa.Column("signals_generated", sa.Integer(), server_default="0"),
        sa.Column("signals_won", sa.Integer(), server_default="0"),
        sa.Column("user_added", sa.Boolean(), server_default="false"),
        sa.Column("user_removed", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("watch_date", "symbol"),
    )
    op.create_index("ix_daily_watchlist_symbol", "daily_watchlist", ["symbol"])
    op.create_index("ix_daily_watchlist_watch_date", "daily_watchlist", ["watch_date"])


def downgrade() -> None:
    op.drop_table("daily_watchlist")
    op.drop_table("screener_results")
    op.drop_table("stock_universe")
