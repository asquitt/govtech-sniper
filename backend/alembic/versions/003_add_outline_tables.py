"""Add proposal_outlines and outline_sections tables.

Revision ID: 003
"""

import sqlalchemy as sa
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "proposal_outlines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "proposal_id",
            sa.Integer(),
            sa.ForeignKey("proposals.id"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("raw_ai_response", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "outline_sections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "outline_id",
            sa.Integer(),
            sa.ForeignKey("proposal_outlines.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("outline_sections.id"), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("mapped_requirement_ids", sa.JSON(), nullable=True, server_default="[]"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_pages", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("outline_sections")
    op.drop_table("proposal_outlines")
