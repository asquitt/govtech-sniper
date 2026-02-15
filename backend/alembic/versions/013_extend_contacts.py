"""Extend contacts with intelligence fields and add agency directory.

Revision ID: 013
"""

import sqlalchemy as sa
from alembic import op

revision = "013"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add intelligence columns to opportunity_contacts
    op.add_column("opportunity_contacts", sa.Column("agency", sa.String(255), nullable=True))
    op.add_column("opportunity_contacts", sa.Column("title", sa.String(255), nullable=True))
    op.add_column("opportunity_contacts", sa.Column("department", sa.String(255), nullable=True))
    op.add_column("opportunity_contacts", sa.Column("location", sa.String(255), nullable=True))
    op.add_column(
        "opportunity_contacts",
        sa.Column("source", sa.String(50), nullable=True, server_default="manual"),
    )
    op.add_column(
        "opportunity_contacts", sa.Column("extraction_confidence", sa.Float(), nullable=True)
    )
    op.add_column("opportunity_contacts", sa.Column("linked_rfp_ids", sa.JSON(), nullable=True))
    op.create_index("ix_opportunity_contacts_agency", "opportunity_contacts", ["agency"])

    # Create agency contact directory table
    op.create_table(
        "agency_contact_database",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("agency_name", sa.String(255), nullable=False, index=True),
        sa.Column("office", sa.String(255), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column(
            "primary_contact_id",
            sa.Integer(),
            sa.ForeignKey("opportunity_contacts.id"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("agency_contact_database")
    op.drop_index("ix_opportunity_contacts_agency", table_name="opportunity_contacts")
    op.drop_column("opportunity_contacts", "linked_rfp_ids")
    op.drop_column("opportunity_contacts", "extraction_confidence")
    op.drop_column("opportunity_contacts", "source")
    op.drop_column("opportunity_contacts", "location")
    op.drop_column("opportunity_contacts", "department")
    op.drop_column("opportunity_contacts", "title")
    op.drop_column("opportunity_contacts", "agency")
