"""Add recipient_role to workspace compliance digest schedules.

Revision ID: 043
Revises: 042
"""

import sqlalchemy as sa
from alembic import op

revision = "043"
down_revision = "042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workspace_compliance_digest_schedules",
        sa.Column(
            "recipient_role",
            sa.String(length=20),
            nullable=False,
            server_default="all",
        ),
    )


def downgrade() -> None:
    op.drop_column("workspace_compliance_digest_schedules", "recipient_role")
