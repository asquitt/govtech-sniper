"""Add step_timestamps JSON column to onboarding_progress."""

import sqlalchemy as sa
from alembic import op

revision = "041"
down_revision = "040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "onboarding_progress",
        sa.Column("step_timestamps", sa.JSON(), server_default="{}", nullable=True),
    )


def downgrade() -> None:
    op.drop_column("onboarding_progress", "step_timestamps")
