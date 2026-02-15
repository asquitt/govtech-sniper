"""Add marketplace columns to proposal_templates table."""

import sqlalchemy as sa
from alembic import op

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "proposal_templates",
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "proposal_templates",
        sa.Column("rating_sum", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "proposal_templates",
        sa.Column("rating_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "proposal_templates",
        sa.Column(
            "forked_from_id",
            sa.Integer(),
            sa.ForeignKey("proposal_templates.id"),
            nullable=True,
        ),
    )
    op.create_index("ix_proposal_templates_is_public", "proposal_templates", ["is_public"])


def downgrade() -> None:
    op.drop_index("ix_proposal_templates_is_public", table_name="proposal_templates")
    op.drop_column("proposal_templates", "forked_from_id")
    op.drop_column("proposal_templates", "rating_count")
    op.drop_column("proposal_templates", "rating_sum")
    op.drop_column("proposal_templates", "is_public")
