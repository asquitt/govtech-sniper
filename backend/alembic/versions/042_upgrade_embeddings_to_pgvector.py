"""Upgrade embeddings from JSON text to pgvector native column."""

import sqlalchemy as sa
from alembic import op

revision = "042"
down_revision = "041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Add native vector column
    op.execute("ALTER TABLE document_embeddings ADD COLUMN embedding vector(768)")

    # Migrate existing JSON data to native vector
    op.execute(
        "UPDATE document_embeddings SET embedding = embedding_json::vector "
        "WHERE embedding_json IS NOT NULL AND embedding_json != ''"
    )

    # Drop old JSON column
    op.drop_column("document_embeddings", "embedding_json")

    # Create HNSW index for fast approximate nearest neighbor search
    op.execute(
        "CREATE INDEX ix_embeddings_hnsw ON document_embeddings "
        "USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_embeddings_hnsw")
    op.add_column(
        "document_embeddings",
        sa.Column("embedding_json", sa.Text(), nullable=True),
    )
    op.execute(
        "UPDATE document_embeddings SET embedding_json = embedding::text "
        "WHERE embedding IS NOT NULL"
    )
    op.execute("ALTER TABLE document_embeddings DROP COLUMN embedding")
