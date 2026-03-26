"""Add positions and exit_signals tables

Revision ID: 003
Revises: 002
"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "positions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(10), nullable=False),
        sa.Column("exchange", sa.String(20), nullable=True),
        sa.Column("direction", sa.String(5), nullable=False),
        sa.Column("status", sa.String(10), nullable=False, server_default="OPEN"),

        # Entry info
        sa.Column("entry_price", sa.Float(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("entry_time", sa.DateTime(), nullable=False),
        sa.Column("entry_signal_id", sa.Integer(), nullable=True),

        # Exit strategy config
        sa.Column("stop_loss_price", sa.Float(), nullable=True),
        sa.Column("profit_target_price", sa.Float(), nullable=True),
        sa.Column("stop_loss_pct", sa.Float(), nullable=True),
        sa.Column("profit_target_pct", sa.Float(), nullable=True),
        sa.Column("use_atr_exits", sa.Boolean(), server_default="true"),
        sa.Column("atr_stop_multiplier", sa.Float(), server_default="1.5"),
        sa.Column("atr_target_multiplier", sa.Float(), server_default="2.5"),
        sa.Column("atr_value_at_entry", sa.Float(), nullable=True),
        sa.Column("eod_exit_enabled", sa.Boolean(), server_default="true"),
        sa.Column("max_hold_bars", sa.Integer(), server_default="60"),

        # Live tracking
        sa.Column("current_price", sa.Float(), nullable=True),
        sa.Column("unrealized_pnl", sa.Float(), nullable=True),
        sa.Column("unrealized_pnl_pct", sa.Float(), nullable=True),
        sa.Column("high_since_entry", sa.Float(), nullable=True),
        sa.Column("low_since_entry", sa.Float(), nullable=True),
        sa.Column("bars_held", sa.Integer(), server_default="0"),
        sa.Column("last_updated", sa.DateTime(), nullable=True),

        # Exit info
        sa.Column("exit_price", sa.Float(), nullable=True),
        sa.Column("exit_time", sa.DateTime(), nullable=True),
        sa.Column("exit_reason", sa.String(30), nullable=True),
        sa.Column("exit_signal_id", sa.Integer(), nullable=True),
        sa.Column("realized_pnl", sa.Float(), nullable=True),
        sa.Column("realized_pnl_pct", sa.Float(), nullable=True),
        sa.Column("realized_pnl_dollar", sa.Float(), nullable=True),

        # Context
        sa.Column("regime_at_entry", sa.String(30), nullable=True),
        sa.Column("regime_at_exit", sa.String(30), nullable=True),
        sa.Column("config_snapshot_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_positions_status", "positions", ["status"])
    op.create_index("ix_positions_symbol_status", "positions", ["symbol", "status"])

    op.create_table(
        "exit_signals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("position_id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(10), nullable=False),
        sa.Column("exit_type", sa.String(30), nullable=False),
        sa.Column("urgency", sa.String(10), nullable=False),
        sa.Column("trigger_price", sa.Float(), nullable=True),
        sa.Column("current_price", sa.Float(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("acknowledged", sa.Boolean(), server_default="false"),
        sa.Column("acted_on", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_exit_signals_position", "exit_signals", ["position_id"])
    op.create_index("ix_exit_signals_unacked", "exit_signals", ["acknowledged"],
                     postgresql_where=sa.text("acknowledged = false"))


def downgrade() -> None:
    op.drop_table("exit_signals")
    op.drop_table("positions")
