"""Add salesforce_field_mappings table.

Revision ID: 010
"""

from alembic import op
import sqlalchemy as sa

revision = "010"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "salesforce_field_mappings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("integration_id", sa.Integer(), sa.ForeignKey("integrations.id"), nullable=False, index=True),
        sa.Column("sniper_field", sa.String(255), nullable=False),
        sa.Column("salesforce_field", sa.String(255), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False, server_default="both"),
        sa.Column("transform", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("salesforce_field_mappings")
