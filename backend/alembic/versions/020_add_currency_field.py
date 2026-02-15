"""Add currency column to rfps table."""

import sqlalchemy as sa
from alembic import op

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "rfps",
        sa.Column("currency", sa.String(10), nullable=False, server_default="USD"),
    )


def downgrade() -> None:
    op.drop_column("rfps", "currency")
