"""Document embeddings for semantic search."""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel, Column, Text


class DocumentEmbedding(SQLModel, table=True):
    """Vector embedding for semantic search.

    NOTE: Uses JSON array instead of pgvector for MVP simplicity.
    Can migrate to pgvector extension later for performance.
    """

    __tablename__ = "document_embeddings"

    id: Optional[int] = Field(default=None, primary_key=True)
    entity_type: str = Field(max_length=50, index=True)
    entity_id: int = Field(index=True)
    chunk_text: str = Field(sa_column=Column(Text))
    chunk_index: int = Field(default=0)
    embedding_json: Optional[str] = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=datetime.utcnow)
