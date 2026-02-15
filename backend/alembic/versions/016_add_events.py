"""Add industry events table."""

import sqlalchemy as sa
from alembic import op

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "industry_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("agency", sa.String(255), nullable=True, index=True),
        sa.Column("event_type", sa.String(50), nullable=False, server_default="industry_day"),
        sa.Column("date", sa.DateTime, nullable=False),
        sa.Column("location", sa.String(500), nullable=True),
        sa.Column("registration_url", sa.String(500), nullable=True),
        sa.Column(
            "related_rfp_id", sa.Integer, sa.ForeignKey("rfps.id"), nullable=True, index=True
        ),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("is_archived", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("industry_events")
