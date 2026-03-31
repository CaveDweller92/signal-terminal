"""Rename max_hold_bars to max_hold_days in positions and parameter_snapshots.

Revision ID: 005
Revises: 004
"""

from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("positions", "max_hold_bars", new_column_name="max_hold_days")
    op.alter_column("parameter_snapshots", "max_hold_bars", new_column_name="max_hold_days")


def downgrade() -> None:
    op.alter_column("positions", "max_hold_days", new_column_name="max_hold_bars")
    op.alter_column("parameter_snapshots", "max_hold_days", new_column_name="max_hold_bars")
