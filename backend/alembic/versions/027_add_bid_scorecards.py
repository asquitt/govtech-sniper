"""Add bid scorecards table.

Revision ID: 027
Revises: 026
Create Date: 2026-02-07
"""

import sqlalchemy as sa
from alembic import op

revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bid_scorecards",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("rfp_id", sa.Integer, sa.ForeignKey("rfps.id"), nullable=False, index=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("criteria_scores", sa.JSON, server_default="[]"),
        sa.Column("overall_score", sa.Float, nullable=True),
        sa.Column("recommendation", sa.String(32), nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("reasoning", sa.Text, nullable=True),
        sa.Column("scorer_type", sa.String(16), nullable=False, server_default="ai"),
        sa.Column("scorer_id", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("bid_scorecards")
