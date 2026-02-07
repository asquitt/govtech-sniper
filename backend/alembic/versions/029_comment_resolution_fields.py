"""Add resolution workflow fields to review_comments.

Revision ID: 029
"""

import sqlalchemy as sa
from alembic import op

revision = "029"
down_revision = "028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "review_comments",
        sa.Column("assigned_to_user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
    )
    op.add_column(
        "review_comments",
        sa.Column("resolved_by_user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
    )
    op.add_column(
        "review_comments",
        sa.Column("verified_by_user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
    )
    op.add_column(
        "review_comments",
        sa.Column("resolved_at", sa.DateTime, nullable=True),
    )
    op.add_column(
        "review_comments",
        sa.Column("verified_at", sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("review_comments", "verified_at")
    op.drop_column("review_comments", "resolved_at")
    op.drop_column("review_comments", "verified_by_user_id")
    op.drop_column("review_comments", "resolved_by_user_id")
    op.drop_column("review_comments", "assigned_to_user_id")
