"""Extend saved_reports with sharing and delivery scheduling fields."""

import sqlalchemy as sa
from alembic import op

revision = "036"
down_revision = "035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "saved_reports",
        sa.Column("is_shared", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "saved_reports",
        sa.Column("shared_with_emails", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "saved_reports",
        sa.Column("delivery_recipients", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "saved_reports",
        sa.Column("delivery_enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "saved_reports", sa.Column("delivery_subject", sa.String(length=255), nullable=True)
    )
    op.add_column("saved_reports", sa.Column("last_delivered_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("saved_reports", "last_delivered_at")
    op.drop_column("saved_reports", "delivery_subject")
    op.drop_column("saved_reports", "delivery_enabled")
    op.drop_column("saved_reports", "delivery_recipients")
    op.drop_column("saved_reports", "shared_with_emails")
    op.drop_column("saved_reports", "is_shared")
