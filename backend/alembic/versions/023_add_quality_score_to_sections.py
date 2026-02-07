"""Add quality_score and quality_breakdown to proposal_sections."""

import sqlalchemy as sa
from alembic import op

revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "proposal_sections",
        sa.Column("quality_score", sa.Float, nullable=True),
    )
    op.add_column(
        "proposal_sections",
        sa.Column("quality_breakdown", sa.JSON, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("proposal_sections", "quality_breakdown")
    op.drop_column("proposal_sections", "quality_score")
