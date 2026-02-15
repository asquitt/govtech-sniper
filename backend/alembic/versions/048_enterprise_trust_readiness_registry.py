"""Add org-scoped compliance registry and checkpoint assessor workflow tables.

Revision ID: 048
Revises: 047
"""

import sqlalchemy as sa
from alembic import op

revision = "048"
down_revision = "047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "compliance_controls",
        sa.Column("organization_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_compliance_controls_organization_id",
        "compliance_controls",
        "organizations",
        ["organization_id"],
        ["id"],
    )
    op.create_index(
        "ix_compliance_controls_organization_id",
        "compliance_controls",
        ["organization_id"],
        unique=False,
    )

    op.add_column(
        "compliance_evidence",
        sa.Column("organization_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_compliance_evidence_organization_id",
        "compliance_evidence",
        "organizations",
        ["organization_id"],
        ["id"],
    )
    op.create_index(
        "ix_compliance_evidence_organization_id",
        "compliance_evidence",
        ["organization_id"],
        unique=False,
    )

    op.execute(
        """
        UPDATE compliance_controls
        SET organization_id = (
            SELECT users.organization_id
            FROM users
            WHERE users.id = compliance_controls.user_id
        )
        WHERE organization_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE compliance_evidence
        SET organization_id = (
            SELECT users.organization_id
            FROM users
            WHERE users.id = compliance_evidence.user_id
        )
        WHERE organization_id IS NULL
        """
    )

    op.create_table(
        "compliance_checkpoint_evidence_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("checkpoint_id", sa.String(length=120), nullable=False),
        sa.Column(
            "evidence_id",
            sa.Integer(),
            sa.ForeignKey("compliance_evidence.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="submitted"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "linked_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("reviewer_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_checkpoint_evidence_org_checkpoint",
        "compliance_checkpoint_evidence_links",
        ["organization_id", "checkpoint_id"],
        unique=False,
    )
    op.create_index(
        "ix_checkpoint_evidence_checkpoint_id",
        "compliance_checkpoint_evidence_links",
        ["checkpoint_id"],
        unique=False,
    )
    op.create_index(
        "ix_checkpoint_evidence_evidence_id",
        "compliance_checkpoint_evidence_links",
        ["evidence_id"],
        unique=False,
    )

    op.create_table(
        "compliance_checkpoint_signoffs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("checkpoint_id", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("assessor_name", sa.String(length=255), nullable=False),
        sa.Column("assessor_org", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("signed_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("signed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_checkpoint_signoff_org_checkpoint",
        "compliance_checkpoint_signoffs",
        ["organization_id", "checkpoint_id"],
        unique=True,
    )
    op.create_index(
        "ix_checkpoint_signoff_checkpoint_id",
        "compliance_checkpoint_signoffs",
        ["checkpoint_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_checkpoint_signoff_checkpoint_id", table_name="compliance_checkpoint_signoffs"
    )
    op.drop_index(
        "ix_checkpoint_signoff_org_checkpoint", table_name="compliance_checkpoint_signoffs"
    )
    op.drop_table("compliance_checkpoint_signoffs")

    op.drop_index(
        "ix_checkpoint_evidence_evidence_id", table_name="compliance_checkpoint_evidence_links"
    )
    op.drop_index(
        "ix_checkpoint_evidence_checkpoint_id", table_name="compliance_checkpoint_evidence_links"
    )
    op.drop_index(
        "ix_checkpoint_evidence_org_checkpoint", table_name="compliance_checkpoint_evidence_links"
    )
    op.drop_table("compliance_checkpoint_evidence_links")

    op.drop_index("ix_compliance_evidence_organization_id", table_name="compliance_evidence")
    op.drop_constraint(
        "fk_compliance_evidence_organization_id", "compliance_evidence", type_="foreignkey"
    )
    op.drop_column("compliance_evidence", "organization_id")

    op.drop_index("ix_compliance_controls_organization_id", table_name="compliance_controls")
    op.drop_constraint(
        "fk_compliance_controls_organization_id", "compliance_controls", type_="foreignkey"
    )
    op.drop_column("compliance_controls", "organization_id")
