"""Add index on rfps.source_type for provider-based queries.

Revision ID: 009
"""

from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_rfps_source_type", "rfps", ["source_type"])


def downgrade() -> None:
    op.drop_index("ix_rfps_source_type", table_name="rfps")
