"""Add assigned_to_user_id and assigned_at to proposal_sections.

Revision ID: 031
"""

import sqlalchemy as sa
from alembic import op

revision = "031"
down_revision = "030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "proposal_sections",
        sa.Column(
            "assigned_to_user_id",
            sa.Integer,
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "proposal_sections",
        sa.Column("assigned_at", sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("proposal_sections", "assigned_at")
    op.drop_column("proposal_sections", "assigned_to_user_id")
