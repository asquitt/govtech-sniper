"""Add capture_activities table for Gantt pipeline view.

Revision ID: 004
"""

from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "capture_activities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "capture_plan_id",
            sa.Integer(),
            sa.ForeignKey("capture_plans.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_milestone", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="planned",
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "depends_on_id",
            sa.Integer(),
            sa.ForeignKey("capture_activities.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("capture_activities")
