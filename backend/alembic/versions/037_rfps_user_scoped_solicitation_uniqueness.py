"""Scope RFP solicitation number uniqueness to user."""

import sqlalchemy as sa
from alembic import op

revision = "037"
down_revision = "036"
branch_labels = None
depends_on = None


def _index_exists(bind, table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(bind)
    indexes = inspector.get_indexes(table_name)
    return any(index.get("name") == index_name for index in indexes)


def upgrade() -> None:
    bind = op.get_bind()

    if _index_exists(bind, "rfps", "ix_rfps_solicitation_number"):
        op.drop_index("ix_rfps_solicitation_number", table_name="rfps")

    op.create_index(
        "ix_rfps_solicitation_number",
        "rfps",
        ["solicitation_number"],
        unique=False,
    )
    op.create_index(
        "ix_rfps_user_solicitation_number",
        "rfps",
        ["user_id", "solicitation_number"],
        unique=True,
    )


def downgrade() -> None:
    bind = op.get_bind()

    if _index_exists(bind, "rfps", "ix_rfps_user_solicitation_number"):
        op.drop_index("ix_rfps_user_solicitation_number", table_name="rfps")

    if _index_exists(bind, "rfps", "ix_rfps_solicitation_number"):
        op.drop_index("ix_rfps_solicitation_number", table_name="rfps")

    op.create_index(
        "ix_rfps_solicitation_number",
        "rfps",
        ["solicitation_number"],
        unique=True,
    )
