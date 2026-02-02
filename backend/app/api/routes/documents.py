"""
RFP Sniper - Document Management Routes
========================================
Knowledge Base document upload and management.
"""

import os
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Path, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.api.deps import get_current_user_optional, resolve_user_id
from app.services.auth_service import UserAuth
from app.models.knowledge_base import KnowledgeBaseDocument, DocumentType, ProcessingStatus
from app.schemas.knowledge_base import (
    DocumentCreate,
    DocumentRead,
    DocumentUpdate,
    DocumentUploadResponse,
    DocumentListItem,
)
from app.config import settings

router = APIRouter(prefix="/documents", tags=["Knowledge Base"])


@router.get("", response_model=List[DocumentListItem])
async def list_documents(
    user_id: Optional[int] = Query(None, description="User ID (optional if authenticated)"),
    document_type: Optional[DocumentType] = Query(None, description="Filter by type"),
    ready_only: bool = Query(False, description="Only show processed documents"),
    current_user: Optional[UserAuth] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> List[DocumentListItem]:
    """
    List all Knowledge Base documents for a user.
    """
    resolved_user_id = resolve_user_id(user_id, current_user)
    query = select(KnowledgeBaseDocument).where(
        KnowledgeBaseDocument.user_id == resolved_user_id
    )
    
    if document_type:
        query = query.where(KnowledgeBaseDocument.document_type == document_type)
    
    if ready_only:
        query = query.where(
            KnowledgeBaseDocument.processing_status == ProcessingStatus.READY
        )
    
    query = query.order_by(KnowledgeBaseDocument.created_at.desc())
    
    result = await session.execute(query)
    documents = result.scalars().all()
    
    return [DocumentListItem.model_validate(doc) for doc in documents]


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(
    document_id: int = Path(..., description="Document ID"),
    session: AsyncSession = Depends(get_session),
) -> DocumentRead:
    """
    Get detailed document information.
    """
    result = await session.execute(
        select(KnowledgeBaseDocument).where(KnowledgeBaseDocument.id == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    
    return DocumentRead.from_orm_with_status(document)


@router.post("", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(..., description="PDF or text file to upload"),
    user_id: Optional[int] = Form(None, description="User ID (optional if authenticated)"),
    title: str = Form(..., description="Document title"),
    document_type: DocumentType = Form(DocumentType.OTHER, description="Document type"),
    description: Optional[str] = Form(None, description="Document description"),
    current_user: Optional[UserAuth] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> DocumentUploadResponse:
    """
    Upload a document to the Knowledge Base.
    
    Supported formats: PDF, TXT, DOC, DOCX
    
    After upload, the document will be processed:
    1. Text extraction (for PDFs)
    2. Chunking for citation tracking
    3. Optional Gemini context caching
    """
    # Validate file type
    allowed_types = {
        "application/pdf": ".pdf",
        "text/plain": ".txt",
        "application/msword": ".doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    }
    
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Allowed: PDF, TXT, DOC, DOCX",
        )
    
    # Check file size
    file_content = await file.read()
    file_size = len(file_content)
    max_size = settings.max_upload_size_mb * 1024 * 1024
    
    if file_size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB",
        )
    
    # Save file
    resolved_user_id = resolve_user_id(user_id, current_user)
    upload_dir = os.path.join(settings.upload_dir, str(resolved_user_id))
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate unique filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(upload_dir, safe_filename)
    
    with open(file_path, "wb") as f:
        f.write(file_content)
    
    # Create database record
    document = KnowledgeBaseDocument(
        user_id=resolved_user_id,
        title=title,
        document_type=document_type,
        description=description,
        original_filename=file.filename,
        file_path=file_path,
        file_size_bytes=file_size,
        mime_type=file.content_type,
        processing_status=ProcessingStatus.PENDING,
    )
    session.add(document)
    await session.commit()
    await session.refresh(document)
    
    # Queue processing task
    from app.tasks.document_tasks import process_document
    process_document.delay(document.id)
    
    return DocumentUploadResponse(
        id=document.id,
        title=document.title,
        original_filename=document.original_filename,
        file_size_bytes=document.file_size_bytes,
        processing_status=document.processing_status,
        message="Document uploaded. Processing will begin shortly.",
    )


@router.patch("/{document_id}", response_model=DocumentRead)
async def update_document(
    document_id: int,
    update_data: DocumentUpdate,
    session: AsyncSession = Depends(get_session),
) -> DocumentRead:
    """
    Update document metadata.
    """
    result = await session.execute(
        select(KnowledgeBaseDocument).where(KnowledgeBaseDocument.id == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    
    # Apply updates
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(document, field, value)
    
    document.updated_at = datetime.utcnow()
    
    await session.commit()
    await session.refresh(document)
    
    return DocumentRead.from_orm_with_status(document)


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Delete a document from the Knowledge Base.
    """
    result = await session.execute(
        select(KnowledgeBaseDocument).where(KnowledgeBaseDocument.id == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    
    # Delete file from disk
    if os.path.exists(document.file_path):
        os.remove(document.file_path)
    
    await session.delete(document)
    await session.commit()
    
    return {"message": f"Document {document_id} deleted"}


@router.get("/types/list")
async def list_document_types() -> List[dict]:
    """
    Get all available document types.
    """
    return [
        {"value": t.value, "label": t.value.replace("_", " ").title()}
        for t in DocumentType
    ]
