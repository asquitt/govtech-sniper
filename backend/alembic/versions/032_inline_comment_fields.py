"""Add inline comment fields to review_comments.

Revision ID: 032
"""

import sqlalchemy as sa
from alembic import op

revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("review_comments", sa.Column("anchor_text", sa.Text, nullable=True))
    op.add_column("review_comments", sa.Column("anchor_offset_start", sa.Integer, nullable=True))
    op.add_column("review_comments", sa.Column("anchor_offset_end", sa.Integer, nullable=True))
    op.add_column(
        "review_comments",
        sa.Column("is_inline", sa.Boolean, nullable=False, server_default="false"),
    )
    op.add_column("review_comments", sa.Column("mentions", sa.JSON, nullable=True))


def downgrade() -> None:
    op.drop_column("review_comments", "mentions")
    op.drop_column("review_comments", "is_inline")
    op.drop_column("review_comments", "anchor_offset_end")
    op.drop_column("review_comments", "anchor_offset_start")
    op.drop_column("review_comments", "anchor_text")
