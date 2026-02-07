"""Extend teaming_partners with discovery fields and add teaming_requests table.

Revision ID: 007
"""

from alembic import op
import sqlalchemy as sa

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to teaming_partners
    op.add_column("teaming_partners", sa.Column("company_duns", sa.String(20), nullable=True))
    op.add_column("teaming_partners", sa.Column("cage_code", sa.String(10), nullable=True))
    op.add_column("teaming_partners", sa.Column("naics_codes", sa.JSON(), nullable=True, server_default="[]"))
    op.add_column("teaming_partners", sa.Column("set_asides", sa.JSON(), nullable=True, server_default="[]"))
    op.add_column("teaming_partners", sa.Column("capabilities", sa.JSON(), nullable=True, server_default="[]"))
    op.add_column("teaming_partners", sa.Column("clearance_level", sa.String(50), nullable=True))
    op.add_column("teaming_partners", sa.Column("past_performance_summary", sa.Text(), nullable=True))
    op.add_column("teaming_partners", sa.Column("website", sa.String(500), nullable=True))
    op.add_column("teaming_partners", sa.Column("is_public", sa.Boolean(), nullable=False, server_default="false"))

    # Create teaming_requests table
    op.create_table(
        "teaming_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("from_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("to_partner_id", sa.Integer(), sa.ForeignKey("teaming_partners.id"), nullable=False, index=True),
        sa.Column("rfp_id", sa.Integer(), sa.ForeignKey("rfps.id"), nullable=True, index=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("teaming_requests")
    op.drop_column("teaming_partners", "is_public")
    op.drop_column("teaming_partners", "website")
    op.drop_column("teaming_partners", "past_performance_summary")
    op.drop_column("teaming_partners", "clearance_level")
    op.drop_column("teaming_partners", "capabilities")
    op.drop_column("teaming_partners", "set_asides")
    op.drop_column("teaming_partners", "naics_codes")
    op.drop_column("teaming_partners", "cage_code")
    op.drop_column("teaming_partners", "company_duns")
