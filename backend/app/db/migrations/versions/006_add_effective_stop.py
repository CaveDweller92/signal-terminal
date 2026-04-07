"""Add effective_stop column to positions.

Revision ID: 006
Revises: 005
"""

import sqlalchemy as sa
from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("positions", sa.Column("effective_stop", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("positions", "effective_stop")
