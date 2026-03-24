"""Initial schema — signals, parameter_snapshots, regime_log, meta_reviews, daily_performance

Revision ID: 001
Revises: None
Create Date: 2026-03-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- signals ---
    op.create_table(
        "signals",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("symbol", sa.String(10), nullable=False, index=True),
        sa.Column("signal_type", sa.String(4), nullable=False),
        sa.Column("conviction", sa.Float, nullable=False),
        sa.Column("tech_score", sa.Float, nullable=False),
        sa.Column("sentiment_score", sa.Float, nullable=False),
        sa.Column("fundamental_score", sa.Float, nullable=False),
        sa.Column("price_at_signal", sa.Float, nullable=False),
        sa.Column("regime_at_signal", sa.String(30), nullable=True),
        sa.Column("config_snapshot_id", sa.Integer, nullable=True),
        sa.Column("reasons", sa.JSON, nullable=True),
        sa.Column("suggested_stop_loss", sa.Float, nullable=True),
        sa.Column("suggested_profit_target", sa.Float, nullable=True),
        sa.Column("atr_at_signal", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("outcome", sa.String(10), nullable=True),
        sa.Column("exit_price", sa.Float, nullable=True),
        sa.Column("return_pct", sa.Float, nullable=True),
        sa.Column("bars_held", sa.Integer, nullable=True),
        sa.Column("outcome_at", sa.DateTime, nullable=True),
    )

    # --- parameter_snapshots ---
    op.create_table(
        "parameter_snapshots",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("snapshot_type", sa.String(20), nullable=False),
        sa.Column("trigger", sa.String(50), nullable=True),
        sa.Column("rsi_period", sa.Integer, server_default="14"),
        sa.Column("rsi_overbought", sa.Integer, server_default="70"),
        sa.Column("rsi_oversold", sa.Integer, server_default="30"),
        sa.Column("ema_fast", sa.Integer, server_default="9"),
        sa.Column("ema_slow", sa.Integer, server_default="21"),
        sa.Column("volume_multiplier", sa.Float, server_default="1.5"),
        sa.Column("min_signal_strength", sa.Float, server_default="2.0"),
        sa.Column("technical_weight", sa.Float, server_default="0.5"),
        sa.Column("sentiment_weight", sa.Float, server_default="0.3"),
        sa.Column("fundamental_weight", sa.Float, server_default="0.2"),
        sa.Column("atr_stop_multiplier", sa.Float, server_default="1.5"),
        sa.Column("atr_target_multiplier", sa.Float, server_default="2.5"),
        sa.Column("default_stop_loss_pct", sa.Float, server_default="2.0"),
        sa.Column("default_profit_target_pct", sa.Float, server_default="3.0"),
        sa.Column("max_hold_bars", sa.Integer, server_default="60"),
        sa.Column("full_config", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # --- regime_log ---
    op.create_table(
        "regime_log",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("regime", sa.String(30), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("previous_regime", sa.String(30), nullable=True),
        sa.Column("detection_method", sa.String(20), server_default="hmm"),
        sa.Column("features", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # --- meta_reviews ---
    op.create_table(
        "meta_reviews",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("review_date", sa.Date, nullable=False, unique=True),
        sa.Column("regime_at_review", sa.String(30), nullable=True),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("recommendations", sa.JSON, nullable=True),
        sa.Column("parameter_adjustments", sa.JSON, nullable=True),
        sa.Column("exit_strategy_assessment", sa.JSON, nullable=True),
        sa.Column("signals_generated", sa.Integer, server_default="0"),
        sa.Column("signals_correct", sa.Integer, server_default="0"),
        sa.Column("avg_return", sa.Float, nullable=True),
        sa.Column("regime_accuracy", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # --- daily_performance ---
    op.create_table(
        "daily_performance",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("perf_date", sa.Date, nullable=False, unique=True),
        sa.Column("total_signals", sa.Integer, server_default="0"),
        sa.Column("buy_signals", sa.Integer, server_default="0"),
        sa.Column("sell_signals", sa.Integer, server_default="0"),
        sa.Column("signals_correct", sa.Integer, server_default="0"),
        sa.Column("signals_incorrect", sa.Integer, server_default="0"),
        sa.Column("win_rate", sa.Float, nullable=True),
        sa.Column("avg_return_pct", sa.Float, nullable=True),
        sa.Column("best_return_pct", sa.Float, nullable=True),
        sa.Column("worst_return_pct", sa.Float, nullable=True),
        sa.Column("total_return_pct", sa.Float, nullable=True),
        sa.Column("regime", sa.String(30), nullable=True),
        sa.Column("config_snapshot_id", sa.Integer, nullable=True),
        sa.Column("breakdown", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("daily_performance")
    op.drop_table("meta_reviews")
    op.drop_table("regime_log")
    op.drop_table("parameter_snapshots")
    op.drop_table("signals")
