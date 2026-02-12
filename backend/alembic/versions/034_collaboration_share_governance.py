"""Add collaboration share-governance fields.

Revision ID: 034
Revises: 033
"""

import sqlalchemy as sa
from alembic import op

revision = "034"
down_revision = "033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "shared_data_permissions",
        sa.Column(
            "requires_approval",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "shared_data_permissions",
        sa.Column(
            "approval_status",
            sa.String(length=20),
            nullable=False,
            server_default="approved",
        ),
    )
    op.add_column(
        "shared_data_permissions",
        sa.Column("approved_by_user_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "shared_data_permissions",
        sa.Column("approved_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "shared_data_permissions",
        sa.Column("expires_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "shared_data_permissions",
        sa.Column("partner_user_id", sa.Integer(), nullable=True),
    )

    op.create_foreign_key(
        "fk_shared_data_permissions_approved_by_user_id_users",
        "shared_data_permissions",
        "users",
        ["approved_by_user_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_shared_data_permissions_partner_user_id_users",
        "shared_data_permissions",
        "users",
        ["partner_user_id"],
        ["id"],
    )
    op.create_index(
        "ix_shared_data_permissions_expires_at",
        "shared_data_permissions",
        ["expires_at"],
    )
    op.create_index(
        "ix_shared_data_permissions_partner_user_id",
        "shared_data_permissions",
        ["partner_user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_shared_data_permissions_partner_user_id", table_name="shared_data_permissions"
    )
    op.drop_index("ix_shared_data_permissions_expires_at", table_name="shared_data_permissions")
    op.drop_constraint(
        "fk_shared_data_permissions_partner_user_id_users",
        "shared_data_permissions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_shared_data_permissions_approved_by_user_id_users",
        "shared_data_permissions",
        type_="foreignkey",
    )

    op.drop_column("shared_data_permissions", "partner_user_id")
    op.drop_column("shared_data_permissions", "expires_at")
    op.drop_column("shared_data_permissions", "approved_at")
    op.drop_column("shared_data_permissions", "approved_by_user_id")
    op.drop_column("shared_data_permissions", "approval_status")
    op.drop_column("shared_data_permissions", "requires_approval")
