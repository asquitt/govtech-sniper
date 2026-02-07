"""Extend user profile with company capability fields.

Revision ID: 025
Revises: 024
Create Date: 2026-02-07
"""

import sqlalchemy as sa
from alembic import op

revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_profiles", sa.Column("company_size", sa.String(20), nullable=True))
    op.add_column("user_profiles", sa.Column("company_duns", sa.String(20), nullable=True))
    op.add_column("user_profiles", sa.Column("cage_code", sa.String(10), nullable=True))
    op.add_column("user_profiles", sa.Column("certifications", sa.JSON, server_default="[]"))
    op.add_column("user_profiles", sa.Column("past_performance_summary", sa.Text, nullable=True))
    op.add_column("user_profiles", sa.Column("core_competencies", sa.JSON, server_default="[]"))
    op.add_column("user_profiles", sa.Column("years_in_business", sa.Integer, nullable=True))
    op.add_column("user_profiles", sa.Column("annual_revenue", sa.Integer, nullable=True))
    op.add_column("user_profiles", sa.Column("employee_count", sa.Integer, nullable=True))
    op.add_column(
        "user_profiles", sa.Column("enabled_sources", sa.JSON, server_default='["sam_gov"]')
    )


def downgrade() -> None:
    op.drop_column("user_profiles", "enabled_sources")
    op.drop_column("user_profiles", "employee_count")
    op.drop_column("user_profiles", "annual_revenue")
    op.drop_column("user_profiles", "years_in_business")
    op.drop_column("user_profiles", "core_competencies")
    op.drop_column("user_profiles", "past_performance_summary")
    op.drop_column("user_profiles", "certifications")
    op.drop_column("user_profiles", "cage_code")
    op.drop_column("user_profiles", "company_duns")
    op.drop_column("user_profiles", "company_size")
