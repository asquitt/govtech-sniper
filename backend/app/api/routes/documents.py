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
from app.api.deps import get_current_user_optional, get_current_user, resolve_user_id
from app.services.auth_service import UserAuth
from app.models.knowledge_base import KnowledgeBaseDocument, DocumentType, ProcessingStatus
from app.schemas.knowledge_base import (
    DocumentCreate,
    DocumentRead,
    DocumentUpdate,
    DocumentUploadResponse,
    DocumentListItem,
    DocumentListResponse,
)
from app.config import settings
from app.services.audit_service import log_audit_event
from app.services.webhook_service import dispatch_webhook_event

router = APIRouter(prefix="/documents", tags=["Knowledge Base"])


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    user_id: Optional[int] = Query(None, description="User ID (optional if authenticated)"),
    document_type: Optional[DocumentType] = Query(None, description="Filter by type"),
    ready_only: bool = Query(False, description="Only show processed documents"),
    current_user: Optional[UserAuth] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> DocumentListResponse:
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

    items = [DocumentListItem.model_validate(doc) for doc in documents]
    return DocumentListResponse(documents=items, total=len(items))


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(
    document_id: int = Path(..., description="Document ID"),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DocumentRead:
    """
    Get detailed document information.
    """
    result = await session.execute(
        select(KnowledgeBaseDocument).where(KnowledgeBaseDocument.id == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document or document.user_id != current_user.id:
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
    await session.flush()
    await log_audit_event(
        session,
        user_id=resolved_user_id,
        entity_type="document",
        entity_id=document.id,
        action="document.uploaded",
        metadata={"title": document.title, "document_type": document.document_type.value},
    )
    await dispatch_webhook_event(
        session,
        user_id=resolved_user_id,
        event_type="document.uploaded",
        payload={
            "document_id": document.id,
            "title": document.title,
            "document_type": document.document_type.value,
        },
    )
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
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DocumentRead:
    """
    Update document metadata.
    """
    result = await session.execute(
        select(KnowledgeBaseDocument).where(KnowledgeBaseDocument.id == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document or document.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    
    # Apply updates
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(document, field, value)
    
    document.updated_at = datetime.utcnow()
    
    await log_audit_event(
        session,
        user_id=document.user_id,
        entity_type="document",
        entity_id=document.id,
        action="document.updated",
        metadata={"updated_fields": list(update_dict.keys())},
    )
    await dispatch_webhook_event(
        session,
        user_id=document.user_id,
        event_type="document.updated",
        payload={
            "document_id": document.id,
            "updated_fields": list(update_dict.keys()),
        },
    )
    await session.commit()
    await session.refresh(document)
    
    return DocumentRead.from_orm_with_status(document)


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Delete a document from the Knowledge Base.
    """
    result = await session.execute(
        select(KnowledgeBaseDocument).where(KnowledgeBaseDocument.id == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document or document.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    
    # Delete file from disk
    if os.path.exists(document.file_path):
        os.remove(document.file_path)
    
    await log_audit_event(
        session,
        user_id=document.user_id,
        entity_type="document",
        entity_id=document.id,
        action="document.deleted",
        metadata={"title": document.title},
    )
    await dispatch_webhook_event(
        session,
        user_id=document.user_id,
        event_type="document.deleted",
        payload={
            "document_id": document.id,
            "title": document.title,
        },
    )
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


@router.get("/stats")
async def get_document_stats(
    current_user: Optional[UserAuth] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Get document statistics for the current user.
    """
    from sqlalchemy import func

    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    total_result = await session.execute(
        select(func.count(KnowledgeBaseDocument.id)).where(
            KnowledgeBaseDocument.user_id == current_user.id
        )
    )
    total = total_result.scalar() or 0

    by_type_result = await session.execute(
        select(
            KnowledgeBaseDocument.document_type,
            func.count(KnowledgeBaseDocument.id),
        )
        .where(KnowledgeBaseDocument.user_id == current_user.id)
        .group_by(KnowledgeBaseDocument.document_type)
    )
    by_type = {row[0].value: row[1] for row in by_type_result.all()}

    return {"total_documents": total, "by_type": by_type}
