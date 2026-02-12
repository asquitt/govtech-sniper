"""Add org invitations and digest schedule models.

Revision ID: 035
Revises: 034
"""

import sqlalchemy as sa
from alembic import op

revision = "035"
down_revision = "034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organization_invitations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("invited_by_user_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="member"),
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("accepted_user_id", sa.Integer(), nullable=True),
        sa.Column("activated_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["invited_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["accepted_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_organization_invitations_organization_id",
        "organization_invitations",
        ["organization_id"],
    )
    op.create_index(
        "ix_organization_invitations_invited_by_user_id",
        "organization_invitations",
        ["invited_by_user_id"],
    )
    op.create_index(
        "ix_organization_invitations_email",
        "organization_invitations",
        ["email"],
    )
    op.create_index(
        "ix_organization_invitations_token",
        "organization_invitations",
        ["token"],
        unique=True,
    )

    op.create_table(
        "workspace_compliance_digest_schedules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("frequency", sa.String(length=20), nullable=False, server_default="weekly"),
        sa.Column("day_of_week", sa.Integer(), nullable=True),
        sa.Column("hour_utc", sa.Integer(), nullable=False, server_default="13"),
        sa.Column("minute_utc", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("channel", sa.String(length=20), nullable=False, server_default="in_app"),
        sa.Column("anomalies_only", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_sent_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["shared_workspaces.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "user_id",
            name="uq_workspace_compliance_digest_workspace_user",
        ),
    )
    op.create_index(
        "ix_workspace_compliance_digest_schedules_workspace_id",
        "workspace_compliance_digest_schedules",
        ["workspace_id"],
    )
    op.create_index(
        "ix_workspace_compliance_digest_schedules_user_id",
        "workspace_compliance_digest_schedules",
        ["user_id"],
    )

    op.create_table(
        "teaming_digest_schedules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("frequency", sa.String(length=20), nullable=False, server_default="weekly"),
        sa.Column("day_of_week", sa.Integer(), nullable=True),
        sa.Column("hour_utc", sa.Integer(), nullable=False, server_default="14"),
        sa.Column("minute_utc", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("channel", sa.String(length=20), nullable=False, server_default="in_app"),
        sa.Column(
            "include_declined_reasons",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_sent_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_teaming_digest_schedule_user"),
    )
    op.create_index(
        "ix_teaming_digest_schedules_user_id",
        "teaming_digest_schedules",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_teaming_digest_schedules_user_id", table_name="teaming_digest_schedules")
    op.drop_table("teaming_digest_schedules")

    op.drop_index(
        "ix_workspace_compliance_digest_schedules_user_id",
        table_name="workspace_compliance_digest_schedules",
    )
    op.drop_index(
        "ix_workspace_compliance_digest_schedules_workspace_id",
        table_name="workspace_compliance_digest_schedules",
    )
    op.drop_table("workspace_compliance_digest_schedules")

    op.drop_index("ix_organization_invitations_token", table_name="organization_invitations")
    op.drop_index("ix_organization_invitations_email", table_name="organization_invitations")
    op.drop_index(
        "ix_organization_invitations_invited_by_user_id",
        table_name="organization_invitations",
    )
    op.drop_index(
        "ix_organization_invitations_organization_id",
        table_name="organization_invitations",
    )
    op.drop_table("organization_invitations")
