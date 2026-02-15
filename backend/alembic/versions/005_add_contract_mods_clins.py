"""Add contract modifications, CLINs, and parent_contract_id + contract_type.

Revision ID: 005
"""

import sqlalchemy as sa
from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add parent_contract_id and contract_type to contract_awards
    op.add_column(
        "contract_awards",
        sa.Column(
            "parent_contract_id",
            sa.Integer(),
            sa.ForeignKey("contract_awards.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_contract_awards_parent_contract_id",
        "contract_awards",
        ["parent_contract_id"],
    )
    op.add_column(
        "contract_awards",
        sa.Column("contract_type", sa.String(50), nullable=True),
    )

    # Contract modifications
    op.create_table(
        "contract_modifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "contract_id",
            sa.Integer(),
            sa.ForeignKey("contract_awards.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("modification_number", sa.String(50), nullable=False),
        sa.Column("mod_type", sa.String(50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("value_change", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Contract CLINs
    op.create_table(
        "contract_clins",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "contract_id",
            sa.Integer(),
            sa.ForeignKey("contract_awards.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("clin_number", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("clin_type", sa.String(20), nullable=True),
        sa.Column("unit_price", sa.Float(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("total_value", sa.Float(), nullable=True),
        sa.Column("funded_amount", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("contract_clins")
    op.drop_table("contract_modifications")
    op.drop_index("ix_contract_awards_parent_contract_id", table_name="contract_awards")
    op.drop_column("contract_awards", "contract_type")
    op.drop_column("contract_awards", "parent_contract_id")
