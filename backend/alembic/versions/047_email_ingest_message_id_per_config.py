"""Scope ingested email message-id uniqueness to each ingest config.

Revision ID: 047
Revises: 046
"""

import sqlalchemy as sa
from alembic import op

revision = "047"
down_revision = "046"
branch_labels = None
depends_on = None


def _unique_constraints() -> list[dict]:
    inspector = sa.inspect(op.get_bind())
    return inspector.get_unique_constraints("ingested_emails")


def _has_unique(columns: list[str]) -> bool:
    target = tuple(columns)
    for constraint in _unique_constraints():
        cols = tuple(constraint.get("column_names") or [])
        if cols == target:
            return True
    return False


def _drop_message_id_unique_constraint() -> None:
    for constraint in _unique_constraints():
        cols = tuple(constraint.get("column_names") or [])
        name = constraint.get("name")
        if cols == ("message_id",) and name:
            op.drop_constraint(name, "ingested_emails", type_="unique")
            break


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        with op.batch_alter_table("ingested_emails", recreate="always") as batch_op:
            batch_op.alter_column(
                "message_id",
                existing_type=sa.String(length=500),
                existing_nullable=False,
                unique=False,
            )
            batch_op.create_unique_constraint(
                "uq_ingested_emails_config_message_id",
                ["config_id", "message_id"],
            )
        return

    _drop_message_id_unique_constraint()
    if not _has_unique(["config_id", "message_id"]):
        op.create_unique_constraint(
            "uq_ingested_emails_config_message_id",
            "ingested_emails",
            ["config_id", "message_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        with op.batch_alter_table("ingested_emails", recreate="always") as batch_op:
            batch_op.drop_constraint("uq_ingested_emails_config_message_id", type_="unique")
            batch_op.create_unique_constraint(
                "uq_ingested_emails_message_id",
                ["message_id"],
            )
        return

    if _has_unique(["config_id", "message_id"]):
        op.drop_constraint(
            "uq_ingested_emails_config_message_id",
            "ingested_emails",
            type_="unique",
        )
    if not _has_unique(["message_id"]):
        op.create_unique_constraint(
            "uq_ingested_emails_message_id",
            "ingested_emails",
            ["message_id"],
        )
