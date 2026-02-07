"""Document embeddings for semantic search."""

from datetime import datetime

from sqlmodel import Column, Field, SQLModel, Text


class DocumentEmbedding(SQLModel, table=True):
    """Vector embedding for semantic search.

    NOTE: Uses JSON array instead of pgvector for MVP simplicity.
    Can migrate to pgvector extension later for performance.
    """

    __tablename__ = "document_embeddings"

    id: int | None = Field(default=None, primary_key=True)
    entity_type: str = Field(max_length=50, index=True)
    entity_id: int = Field(index=True)
    chunk_text: str = Field(sa_column=Column(Text))
    chunk_index: int = Field(default=0)
    embedding_json: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=datetime.utcnow)
