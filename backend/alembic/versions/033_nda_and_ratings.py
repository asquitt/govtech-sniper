"""Create teaming_ndas and teaming_performance_ratings tables.

Revision ID: 033
"""

import sqlalchemy as sa
from alembic import op

revision = "033"
down_revision = "032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "teaming_ndas",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column(
            "partner_id",
            sa.Integer,
            sa.ForeignKey("teaming_partners.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("rfp_id", sa.Integer, sa.ForeignKey("rfps.id"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("signed_date", sa.Date, nullable=True),
        sa.Column("expiry_date", sa.Date, nullable=True),
        sa.Column("document_path", sa.String(500), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "teaming_performance_ratings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column(
            "partner_id",
            sa.Integer,
            sa.ForeignKey("teaming_partners.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("rfp_id", sa.Integer, sa.ForeignKey("rfps.id"), nullable=True),
        sa.Column("rating", sa.Integer, nullable=False),
        sa.Column("responsiveness", sa.Integer, nullable=True),
        sa.Column("quality", sa.Integer, nullable=True),
        sa.Column("timeliness", sa.Integer, nullable=True),
        sa.Column("comment", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("teaming_performance_ratings")
    op.drop_table("teaming_ndas")
