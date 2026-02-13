"""Document embeddings for semantic search using pgvector."""

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column as SAColumn
from sqlmodel import Column, Field, SQLModel, Text


class DocumentEmbedding(SQLModel, table=True):
    """Vector embedding for semantic search using pgvector HNSW index."""

    __tablename__ = "document_embeddings"

    id: int | None = Field(default=None, primary_key=True)
    entity_type: str = Field(max_length=50, index=True)
    entity_id: int = Field(index=True)
    chunk_text: str = Field(sa_column=Column(Text))
    chunk_index: int = Field(default=0)
    embedding: list[float] | None = Field(
        default=None,
        sa_column=SAColumn(Vector(768)),
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
