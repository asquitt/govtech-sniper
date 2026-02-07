"""Add proposal_focus_documents table.

Revision ID: 002
"""

from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "proposal_focus_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("proposal_id", sa.Integer(), sa.ForeignKey("proposals.id"), nullable=False, index=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("knowledge_base_documents.id"), nullable=False, index=True),
        sa.Column("priority_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("proposal_focus_documents")
