"""Add writing_plan column to proposal_sections.

Revision ID: 001
"""

from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "proposal_sections",
        sa.Column("writing_plan", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("proposal_sections", "writing_plan")
