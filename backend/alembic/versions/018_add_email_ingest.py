"""Add email ingest configs and ingested emails tables."""

from alembic import op
import sqlalchemy as sa

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "email_ingest_configs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("imap_server", sa.String(255), nullable=False),
        sa.Column("imap_port", sa.Integer, nullable=False, server_default="993"),
        sa.Column("email_address", sa.String(255), nullable=False),
        sa.Column("encrypted_password", sa.String(500), nullable=False),
        sa.Column("folder", sa.String(255), nullable=False, server_default="INBOX"),
        sa.Column("is_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("last_checked_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "ingested_emails",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("config_id", sa.Integer, sa.ForeignKey("email_ingest_configs.id"), nullable=False, index=True),
        sa.Column("message_id", sa.String(500), nullable=False, unique=True),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("sender", sa.String(255), nullable=False),
        sa.Column("received_at", sa.DateTime, nullable=False),
        sa.Column("body_text", sa.Text, nullable=True),
        sa.Column("processing_status", sa.String(20), nullable=False, server_default="pending", index=True),
        sa.Column("created_rfp_id", sa.Integer, sa.ForeignKey("rfps.id"), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("ingested_emails")
    op.drop_table("email_ingest_configs")
