"""Add workspace compliance digest delivery attempts table.

Revision ID: 044
Revises: 043
"""

import sqlalchemy as sa
from alembic import op

revision = "044"
down_revision = "043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspace_compliance_digest_deliveries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("schedule_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="success"),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("retry_of_delivery_id", sa.Integer(), nullable=True),
        sa.Column("channel", sa.String(length=20), nullable=False, server_default="in_app"),
        sa.Column("recipient_role", sa.String(length=20), nullable=False, server_default="all"),
        sa.Column("recipient_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("anomalies_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failure_reason", sa.String(length=255), nullable=True),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["shared_workspaces.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["schedule_id"],
            ["workspace_compliance_digest_schedules.id"],
        ),
        sa.ForeignKeyConstraint(
            ["retry_of_delivery_id"],
            ["workspace_compliance_digest_deliveries.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_workspace_compliance_digest_deliveries_workspace_id",
        "workspace_compliance_digest_deliveries",
        ["workspace_id"],
    )
    op.create_index(
        "ix_workspace_compliance_digest_deliveries_user_id",
        "workspace_compliance_digest_deliveries",
        ["user_id"],
    )
    op.create_index(
        "ix_workspace_compliance_digest_deliveries_schedule_id",
        "workspace_compliance_digest_deliveries",
        ["schedule_id"],
    )
    op.create_index(
        "ix_workspace_compliance_digest_deliveries_retry_of_delivery_id",
        "workspace_compliance_digest_deliveries",
        ["retry_of_delivery_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_workspace_compliance_digest_deliveries_retry_of_delivery_id",
        table_name="workspace_compliance_digest_deliveries",
    )
    op.drop_index(
        "ix_workspace_compliance_digest_deliveries_schedule_id",
        table_name="workspace_compliance_digest_deliveries",
    )
    op.drop_index(
        "ix_workspace_compliance_digest_deliveries_user_id",
        table_name="workspace_compliance_digest_deliveries",
    )
    op.drop_index(
        "ix_workspace_compliance_digest_deliveries_workspace_id",
        table_name="workspace_compliance_digest_deliveries",
    )
    op.drop_table("workspace_compliance_digest_deliveries")
