"""Add review checklist items table, due dates on assignments, go/no-go on reviews.

Revision ID: 028
"""

import sqlalchemy as sa
from alembic import op

revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "review_checklist_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "review_id",
            sa.Integer,
            sa.ForeignKey("proposal_reviews.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("item_text", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("reviewer_note", sa.Text, nullable=True),
        sa.Column("display_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    op.add_column("review_assignments", sa.Column("due_date", sa.DateTime, nullable=True))
    op.add_column("review_assignments", sa.Column("completed_at", sa.DateTime, nullable=True))
    op.add_column("proposal_reviews", sa.Column("go_no_go_decision", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("proposal_reviews", "go_no_go_decision")
    op.drop_column("review_assignments", "completed_at")
    op.drop_column("review_assignments", "due_date")
    op.drop_table("review_checklist_items")
