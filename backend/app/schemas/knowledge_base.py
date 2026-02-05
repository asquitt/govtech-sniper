"""
RFP Sniper - Knowledge Base Schemas
===================================
Request/Response models for document uploads.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, computed_field

from app.models.knowledge_base import DocumentType, ProcessingStatus


# =============================================================================
# Document Schemas
# =============================================================================

class DocumentCreate(BaseModel):
    """Schema for creating document metadata."""
    title: str = Field(max_length=255)
    document_type: DocumentType = Field(default=DocumentType.OTHER)
    description: Optional[str] = Field(default=None, max_length=1000)
    tags: List[str] = Field(default=[])


class DocumentRead(BaseModel):
    """Schema for reading document data."""
    id: int
    user_id: int
    title: str
    document_type: DocumentType
    description: Optional[str]
    original_filename: str
    file_size_bytes: int
    mime_type: str
    page_count: Optional[int]
    processing_status: ProcessingStatus
    processing_error: Optional[str]
    gemini_cache_name: Optional[str]
    gemini_cache_expires_at: Optional[datetime]
    extracted_metadata: Dict
    tags: List[str]
    times_cited: int
    last_cited_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime]
    is_ready: bool = False

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_status(cls, document) -> "DocumentRead":
        """Create from ORM with computed fields."""
        data = {
            "id": document.id,
            "user_id": document.user_id,
            "title": document.title,
            "document_type": document.document_type,
            "description": document.description,
            "original_filename": document.original_filename,
            "file_size_bytes": document.file_size_bytes,
            "mime_type": document.mime_type,
            "page_count": document.page_count,
            "processing_status": document.processing_status,
            "processing_error": document.processing_error,
            "gemini_cache_name": document.gemini_cache_name,
            "gemini_cache_expires_at": document.gemini_cache_expires_at,
            "extracted_metadata": document.extracted_metadata,
            "tags": document.tags,
            "times_cited": document.times_cited,
            "last_cited_at": document.last_cited_at,
            "created_at": document.created_at,
            "updated_at": document.updated_at,
            "processed_at": document.processed_at,
            "is_ready": document.processing_status == ProcessingStatus.READY,
        }
        return cls(**data)


class DocumentUpdate(BaseModel):
    """Schema for updating document metadata."""
    title: Optional[str] = Field(default=None, max_length=255)
    document_type: Optional[DocumentType] = None
    description: Optional[str] = Field(default=None, max_length=1000)
    tags: Optional[List[str]] = None


class DocumentUploadResponse(BaseModel):
    """Response from document upload endpoint."""
    id: int
    title: str
    original_filename: str
    file_size_bytes: int
    processing_status: ProcessingStatus
    message: str


class DocumentListItem(BaseModel):
    """Condensed document for list views."""
    id: int
    title: str
    document_type: DocumentType
    description: Optional[str] = None
    original_filename: str
    processing_status: ProcessingStatus
    file_size_bytes: int
    times_cited: int
    created_at: datetime

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def is_ready(self) -> bool:
        return self.processing_status == ProcessingStatus.READY


class DocumentListResponse(BaseModel):
    """Response for document list endpoints."""
    documents: List[DocumentListItem]
    total: int
