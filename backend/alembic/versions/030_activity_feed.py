"""Create activity_feed table.

Revision ID: 030
"""

import sqlalchemy as sa
from alembic import op

revision = "030"
down_revision = "029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "activity_feed",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "proposal_id",
            sa.Integer,
            sa.ForeignKey("proposals.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("activity_type", sa.String(50), nullable=False),
        sa.Column("summary", sa.String(500), nullable=False),
        sa.Column(
            "section_id",
            sa.Integer,
            sa.ForeignKey("proposal_sections.id"),
            nullable=True,
        ),
        sa.Column("metadata_json", sa.JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
            index=True,
        ),
    )
    op.create_index(
        "ix_activity_feed_proposal_created",
        "activity_feed",
        ["proposal_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_activity_feed_proposal_created")
    op.drop_table("activity_feed")
