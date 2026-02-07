"""Add SharePoint sync config and logs tables.

Revision ID: 024
Revises: 023
Create Date: 2026-02-07
"""

import sqlalchemy as sa
from alembic import op

revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sharepoint_sync_configs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column(
            "proposal_id", sa.Integer, sa.ForeignKey("proposals.id"), nullable=False, index=True
        ),
        sa.Column("sharepoint_folder", sa.String(512), nullable=False),
        sa.Column("sync_direction", sa.String(32), nullable=False, server_default="push"),
        sa.Column("auto_sync_enabled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("watch_for_rfps", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("last_synced_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "sharepoint_sync_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "config_id",
            sa.Integer,
            sa.ForeignKey("sharepoint_sync_configs.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, index=True),
        sa.Column("details", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("sharepoint_sync_logs")
    op.drop_table("sharepoint_sync_configs")
