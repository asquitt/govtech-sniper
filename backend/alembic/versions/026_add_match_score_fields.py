"""Add match score fields to RFPs table.

Revision ID: 026
Revises: 025
Create Date: 2026-02-07
"""

import sqlalchemy as sa
from alembic import op

revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("rfps", sa.Column("match_score", sa.Float, nullable=True))
    op.add_column("rfps", sa.Column("match_reasoning", sa.Text, nullable=True))
    op.add_column("rfps", sa.Column("match_details", sa.JSON, nullable=True))


def downgrade() -> None:
    op.drop_column("rfps", "match_details")
    op.drop_column("rfps", "match_reasoning")
    op.drop_column("rfps", "match_score")
