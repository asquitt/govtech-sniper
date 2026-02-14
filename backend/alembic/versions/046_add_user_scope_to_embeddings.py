"""Add user scoping to document embeddings for tenant-isolated semantic search."""

import sqlalchemy as sa
from alembic import op

revision = "046"
down_revision = "045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    op.add_column("document_embeddings", sa.Column("user_id", sa.Integer(), nullable=True))
    op.create_index(
        "ix_document_embeddings_user_id",
        "document_embeddings",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_embeddings_user_entity",
        "document_embeddings",
        ["user_id", "entity_type", "entity_id"],
        unique=False,
    )

    if dialect == "postgresql":
        op.execute(
            """
            UPDATE document_embeddings AS e
            SET user_id = r.user_id
            FROM rfps AS r
            WHERE e.entity_type = 'rfp'
              AND e.entity_id = r.id
              AND e.user_id IS NULL
            """
        )
        op.execute(
            """
            UPDATE document_embeddings AS e
            SET user_id = p.user_id
            FROM proposal_sections AS s
            JOIN proposals AS p ON p.id = s.proposal_id
            WHERE e.entity_type = 'proposal_section'
              AND e.entity_id = s.id
              AND e.user_id IS NULL
            """
        )
        op.execute(
            """
            UPDATE document_embeddings AS e
            SET user_id = d.user_id
            FROM knowledge_base_documents AS d
            WHERE e.entity_type = 'knowledge_doc'
              AND e.entity_id = d.id
              AND e.user_id IS NULL
            """
        )
        op.execute(
            """
            UPDATE document_embeddings AS e
            SET user_id = c.user_id
            FROM opportunity_contacts AS c
            WHERE e.entity_type = 'contact'
              AND e.entity_id = c.id
              AND e.user_id IS NULL
            """
        )
    else:
        # SQLite fallback syntax (correlated subqueries, no UPDATE..FROM support).
        op.execute(
            """
            UPDATE document_embeddings
            SET user_id = (
                SELECT rfps.user_id
                FROM rfps
                WHERE rfps.id = document_embeddings.entity_id
            )
            WHERE entity_type = 'rfp' AND user_id IS NULL
            """
        )
        op.execute(
            """
            UPDATE document_embeddings
            SET user_id = (
                SELECT proposals.user_id
                FROM proposal_sections
                JOIN proposals ON proposals.id = proposal_sections.proposal_id
                WHERE proposal_sections.id = document_embeddings.entity_id
            )
            WHERE entity_type = 'proposal_section' AND user_id IS NULL
            """
        )
        op.execute(
            """
            UPDATE document_embeddings
            SET user_id = (
                SELECT knowledge_base_documents.user_id
                FROM knowledge_base_documents
                WHERE knowledge_base_documents.id = document_embeddings.entity_id
            )
            WHERE entity_type = 'knowledge_doc' AND user_id IS NULL
            """
        )
        op.execute(
            """
            UPDATE document_embeddings
            SET user_id = (
                SELECT opportunity_contacts.user_id
                FROM opportunity_contacts
                WHERE opportunity_contacts.id = document_embeddings.entity_id
            )
            WHERE entity_type = 'contact' AND user_id IS NULL
            """
        )


def downgrade() -> None:
    op.drop_index("ix_document_embeddings_user_entity", table_name="document_embeddings")
    op.drop_index("ix_document_embeddings_user_id", table_name="document_embeddings")
    op.drop_column("document_embeddings", "user_id")
