"""Add market signals and signal subscriptions tables."""

from alembic import op
import sqlalchemy as sa

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_signals",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("signal_type", sa.String(50), nullable=False, server_default="news"),
        sa.Column("agency", sa.String(255), nullable=True, index=True),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("relevance_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("published_at", sa.DateTime, nullable=True),
        sa.Column("is_read", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "signal_subscriptions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("agencies", sa.JSON, nullable=True),
        sa.Column("naics_codes", sa.JSON, nullable=True),
        sa.Column("keywords", sa.JSON, nullable=True),
        sa.Column("email_digest_enabled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("digest_frequency", sa.String(20), nullable=False, server_default="daily"),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("signal_subscriptions")
    op.drop_table("market_signals")
