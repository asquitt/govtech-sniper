"""Add past performance metadata to knowledge base documents."""

import sqlalchemy as sa
from alembic import op

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "knowledge_base_documents", sa.Column("contract_number", sa.String(50), nullable=True)
    )
    op.add_column(
        "knowledge_base_documents", sa.Column("performing_agency", sa.String(255), nullable=True)
    )
    op.add_column("knowledge_base_documents", sa.Column("contract_value", sa.Float, nullable=True))
    op.add_column(
        "knowledge_base_documents",
        sa.Column("period_of_performance_start", sa.DateTime, nullable=True),
    )
    op.add_column(
        "knowledge_base_documents",
        sa.Column("period_of_performance_end", sa.DateTime, nullable=True),
    )
    op.add_column("knowledge_base_documents", sa.Column("naics_code", sa.String(10), nullable=True))
    op.add_column("knowledge_base_documents", sa.Column("relevance_tags", sa.JSON, nullable=True))
    op.create_index(
        "ix_knowledge_base_documents_performing_agency",
        "knowledge_base_documents",
        ["performing_agency"],
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_base_documents_performing_agency")
    op.drop_column("knowledge_base_documents", "relevance_tags")
    op.drop_column("knowledge_base_documents", "naics_code")
    op.drop_column("knowledge_base_documents", "period_of_performance_end")
    op.drop_column("knowledge_base_documents", "period_of_performance_start")
    op.drop_column("knowledge_base_documents", "contract_value")
    op.drop_column("knowledge_base_documents", "performing_agency")
    op.drop_column("knowledge_base_documents", "contract_number")
