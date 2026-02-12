"""Add compliance control-evidence registry tables."""

import sqlalchemy as sa
from alembic import op

revision = "040"
down_revision = "039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "compliance_controls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("framework", sa.String(50), nullable=False),
        sa.Column("control_id", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="not_started"),
        sa.Column("implementation_notes", sa.Text(), nullable=True),
        sa.Column("assessor_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "compliance_evidence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("evidence_type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("url", sa.String(500), nullable=True),
        sa.Column("collected_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "control_evidence_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "control_id",
            sa.Integer(),
            sa.ForeignKey("compliance_controls.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "evidence_id",
            sa.Integer(),
            sa.ForeignKey("compliance_evidence.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("linked_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("control_evidence_links")
    op.drop_table("compliance_evidence")
    op.drop_table("compliance_controls")
