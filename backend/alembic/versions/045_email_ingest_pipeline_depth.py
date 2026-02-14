"""Extend email ingest config and history for pipeline depth.

Revision ID: 045
Revises: 044
"""

import sqlalchemy as sa
from alembic import op

revision = "045"
down_revision = "044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "email_ingest_configs",
        sa.Column("workspace_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "email_ingest_configs",
        sa.Column("auto_create_rfps", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "email_ingest_configs",
        sa.Column(
            "min_rfp_confidence",
            sa.Float(),
            nullable=False,
            server_default="0.35",
        ),
    )
    op.create_foreign_key(
        "fk_email_ingest_configs_workspace_id",
        "email_ingest_configs",
        "shared_workspaces",
        ["workspace_id"],
        ["id"],
    )
    op.create_index(
        "ix_email_ingest_configs_workspace_id",
        "email_ingest_configs",
        ["workspace_id"],
    )

    op.add_column(
        "ingested_emails",
        sa.Column("attachment_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "ingested_emails",
        sa.Column(
            "attachment_names",
            sa.JSON(),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "ingested_emails",
        sa.Column("classification_confidence", sa.Float(), nullable=True),
    )
    op.add_column(
        "ingested_emails",
        sa.Column(
            "classification_reasons",
            sa.JSON(),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "ingested_emails",
        sa.Column("processed_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ingested_emails", "processed_at")
    op.drop_column("ingested_emails", "classification_reasons")
    op.drop_column("ingested_emails", "classification_confidence")
    op.drop_column("ingested_emails", "attachment_names")
    op.drop_column("ingested_emails", "attachment_count")

    op.drop_index(
        "ix_email_ingest_configs_workspace_id",
        table_name="email_ingest_configs",
    )
    op.drop_constraint(
        "fk_email_ingest_configs_workspace_id",
        "email_ingest_configs",
        type_="foreignkey",
    )
    op.drop_column("email_ingest_configs", "min_rfp_confidence")
    op.drop_column("email_ingest_configs", "auto_create_rfps")
    op.drop_column("email_ingest_configs", "workspace_id")
