"""Add workflow rules and execution history tables."""

import sqlalchemy as sa
from alembic import op

revision = "019"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_rules",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("trigger_type", sa.String(50), nullable=False, index=True),
        sa.Column("conditions", sa.JSON, nullable=True),
        sa.Column("actions", sa.JSON, nullable=True),
        sa.Column("priority", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "workflow_executions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "rule_id", sa.Integer, sa.ForeignKey("workflow_rules.id"), nullable=False, index=True
        ),
        sa.Column("triggered_at", sa.DateTime, nullable=False, index=True),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.Integer, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("result", sa.JSON, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("workflow_executions")
    op.drop_table("workflow_rules")
