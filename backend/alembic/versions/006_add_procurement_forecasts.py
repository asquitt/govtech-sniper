"""Add procurement forecasts and forecast alerts tables.

Revision ID: 006
"""

import sqlalchemy as sa
from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "procurement_forecasts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("agency", sa.String(255), nullable=True, index=True),
        sa.Column("naics_code", sa.String(10), nullable=True, index=True),
        sa.Column("estimated_value", sa.Float(), nullable=True),
        sa.Column("expected_solicitation_date", sa.Date(), nullable=True),
        sa.Column("expected_award_date", sa.Date(), nullable=True),
        sa.Column("fiscal_year", sa.Integer(), nullable=True, index=True),
        sa.Column("source", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "linked_rfp_id", sa.Integer(), sa.ForeignKey("rfps.id"), nullable=True, index=True
        ),
        sa.Column("match_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "forecast_alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column(
            "forecast_id",
            sa.Integer(),
            sa.ForeignKey("procurement_forecasts.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("rfp_id", sa.Integer(), sa.ForeignKey("rfps.id"), nullable=False, index=True),
        sa.Column("match_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("match_reason", sa.Text(), nullable=True),
        sa.Column("is_dismissed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("forecast_alerts")
    op.drop_table("procurement_forecasts")
