"""Add FK indexes to proposal_versions table."""

from alembic import op

revision = "049"
down_revision = "048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_proposal_versions_user_id", "proposal_versions", ["user_id"])
    op.create_index("ix_proposal_versions_section_id", "proposal_versions", ["section_id"])


def downgrade() -> None:
    op.drop_index("ix_proposal_versions_section_id", "proposal_versions")
    op.drop_index("ix_proposal_versions_user_id", "proposal_versions")
