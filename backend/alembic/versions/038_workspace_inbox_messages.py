"""Add workspace inbox messages table.

Revision ID: 038
Revises: 037
"""

import sqlalchemy as sa
from alembic import op

revision = "038"
down_revision = "037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inbox_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("sender_id", sa.Integer(), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "message_type",
            sa.String(length=50),
            nullable=False,
            server_default="general",
        ),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("read_by", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("attachments", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["workspace_id"], ["shared_workspaces.id"]),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"]),
    )
    op.create_index("ix_inbox_messages_workspace_id", "inbox_messages", ["workspace_id"])
    op.create_index("ix_inbox_messages_sender_id", "inbox_messages", ["sender_id"])


def downgrade() -> None:
    op.drop_index("ix_inbox_messages_sender_id", table_name="inbox_messages")
    op.drop_index("ix_inbox_messages_workspace_id", table_name="inbox_messages")
    op.drop_table("inbox_messages")
