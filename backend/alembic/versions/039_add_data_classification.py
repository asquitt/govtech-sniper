"""Add data classification field to core entities for CUI/FCI policy enforcement."""

import sqlalchemy as sa
from alembic import op

revision = "039"
down_revision = "038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "proposals",
        sa.Column("classification", sa.String(20), nullable=False, server_default="internal"),
    )
    op.add_column(
        "rfps",
        sa.Column("classification", sa.String(20), nullable=False, server_default="internal"),
    )
    op.add_column(
        "knowledge_base_documents",
        sa.Column("classification", sa.String(20), nullable=False, server_default="internal"),
    )
    op.add_column(
        "contract_awards",
        sa.Column("classification", sa.String(20), nullable=False, server_default="internal"),
    )


def downgrade() -> None:
    op.drop_column("contract_awards", "classification")
    op.drop_column("knowledge_base_documents", "classification")
    op.drop_column("rfps", "classification")
    op.drop_column("proposals", "classification")
