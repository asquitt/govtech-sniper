"""
RFP Sniper - Knowledge Base Models
==================================
User-uploaded documents for RAG (Resumes, Past Performance, etc.)
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from enum import Enum

from sqlmodel import Field, Relationship, SQLModel, Column, JSON, Text

if TYPE_CHECKING:
    from app.models.user import User


class DocumentType(str, Enum):
    """Type of knowledge base document."""
    RESUME = "resume"
    PAST_PERFORMANCE = "past_performance"
    CAPABILITY_STATEMENT = "capability_statement"
    TECHNICAL_SPEC = "technical_spec"
    CASE_STUDY = "case_study"
    CERTIFICATION = "certification"
    CONTRACT = "contract"
    OTHER = "other"


class ProcessingStatus(str, Enum):
    """Status of document processing pipeline."""
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"


# =============================================================================
# Knowledge Base Document Model
# =============================================================================

class KnowledgeBaseDocumentBase(SQLModel):
    """Base document fields."""
    title: str = Field(max_length=255)
    document_type: DocumentType = Field(default=DocumentType.OTHER)
    description: Optional[str] = Field(default=None, max_length=1000)


class KnowledgeBaseDocument(KnowledgeBaseDocumentBase, table=True):
    """
    User-uploaded document for RAG context.
    
    These documents are uploaded to Gemini's Context Caching API
    to enable citing specific sources in generated proposals.
    """
    __tablename__ = "knowledge_base_documents"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    
    # File metadata
    original_filename: str = Field(max_length=255)
    file_path: str = Field(max_length=500)
    file_size_bytes: int = Field(default=0)
    mime_type: str = Field(max_length=100, default="application/pdf")
    page_count: Optional[int] = None
    
    # Processing status
    processing_status: ProcessingStatus = Field(default=ProcessingStatus.PENDING)
    processing_error: Optional[str] = Field(default=None, sa_column=Column(Text))
    
    # Extracted content
    full_text: Optional[str] = Field(default=None, sa_column=Column(Text))
    
    # Gemini Context Caching
    # When uploaded to Gemini, we store the cache reference
    gemini_cache_name: Optional[str] = Field(default=None, max_length=255)
    gemini_cache_expires_at: Optional[datetime] = None
    
    # Metadata extracted from document
    extracted_metadata: dict = Field(default={}, sa_column=Column(JSON))
    
    # Tags for filtering
    tags: List[str] = Field(default=[], sa_column=Column(JSON))
    
    # Usage tracking
    times_cited: int = Field(default=0)
    last_cited_at: Optional[datetime] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    
    # Relationship
    user: Optional["User"] = Relationship(back_populates="documents")
    chunks: List["DocumentChunk"] = Relationship(back_populates="document")


# =============================================================================
# Document Chunk Model (for fine-grained citations)
# =============================================================================

class DocumentChunk(SQLModel, table=True):
    """
    Chunk of a document for citation tracking.
    
    While we use Gemini's massive context window instead of vector search,
    we still need to track chunks for accurate page-level citations.
    """
    __tablename__ = "document_chunks"

    id: Optional[int] = Field(default=None, primary_key=True)
    document_id: int = Field(foreign_key="knowledge_base_documents.id", index=True)
    
    # Chunk content
    content: str = Field(sa_column=Column(Text))
    
    # Location in source document
    page_number: int = Field(default=1)
    start_char: int = Field(default=0)
    end_char: int = Field(default=0)
    
    # Chunk metadata
    chunk_index: int = Field(default=0)  # Order within document
    word_count: int = Field(default=0)
    
    # For citation matching
    # When AI generates [[Source: file.pdf, Page 12]], we match to chunks
    content_hash: Optional[str] = Field(default=None, max_length=64)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationship
    document: Optional[KnowledgeBaseDocument] = Relationship(back_populates="chunks")

