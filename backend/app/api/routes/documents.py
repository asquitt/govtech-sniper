"""
RFP Sniper - Document Management Routes
========================================
Knowledge Base document upload and management.
"""

import os
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user, get_current_user_optional, resolve_user_id
from app.config import settings
from app.database import get_session
from app.models.knowledge_base import DocumentType, KnowledgeBaseDocument, ProcessingStatus
from app.schemas.knowledge_base import (
    DocumentListItem,
    DocumentListResponse,
    DocumentRead,
    DocumentUpdate,
    DocumentUploadResponse,
)
from app.services.audit_service import log_audit_event
from app.services.auth_service import UserAuth
from app.services.webhook_service import dispatch_webhook_event

router = APIRouter(prefix="/documents", tags=["Knowledge Base"])


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    user_id: int | None = Query(None, description="User ID (optional if authenticated)"),
    document_type: DocumentType | None = Query(None, description="Filter by type"),
    ready_only: bool = Query(False, description="Only show processed documents"),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> DocumentListResponse:
    """
    List all Knowledge Base documents for a user.
    """
    resolved_user_id = resolve_user_id(user_id, current_user)
    query = select(KnowledgeBaseDocument).where(KnowledgeBaseDocument.user_id == resolved_user_id)

    if document_type:
        query = query.where(KnowledgeBaseDocument.document_type == document_type)

    if ready_only:
        query = query.where(KnowledgeBaseDocument.processing_status == ProcessingStatus.READY)

    query = query.order_by(KnowledgeBaseDocument.created_at.desc())

    result = await session.execute(query)
    documents = result.scalars().all()

    items = [DocumentListItem.model_validate(doc) for doc in documents]
    return DocumentListResponse(documents=items, total=len(items))


@router.get("/types/list")
async def list_document_types() -> list[dict]:
    """
    Get all available document types.
    """
    return [{"value": t.value, "label": t.value.replace("_", " ").title()} for t in DocumentType]


@router.get("/stats")
async def get_document_stats(
    current_user: UserAuth | None = Depends(get_current_user_optional),
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
    user_id: int | None = Form(None, description="User ID (optional if authenticated)"),
    title: str = Form(..., description="Document title"),
    document_type: DocumentType = Form(DocumentType.OTHER, description="Document type"),
    description: str | None = Form(None, description="Document description"),
    current_user: UserAuth | None = Depends(get_current_user_optional),
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

    # Queue processing task (non-fatal if broker unavailable)
    try:
        from app.tasks.document_tasks import process_document

        process_document.delay(document.id)
    except Exception:
        import structlog

        structlog.get_logger().warning(
            "Failed to queue document processing", document_id=document.id
        )

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


# === Past Performance Endpoints ===

from app.schemas.past_performance import (
    MatchResponse,
    MatchResult,
    NarrativeResponse,
    PastPerformanceListResponse,
    PastPerformanceMetadata,
    PastPerformanceRead,
)
from app.services.past_performance_matcher import generate_narrative, match_past_performances


@router.post(
    "/documents/{document_id}/past-performance-metadata", response_model=PastPerformanceRead
)
async def add_past_performance_metadata(
    document_id: int,
    payload: PastPerformanceMetadata,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PastPerformanceRead:
    """Add or update past performance metadata on a document."""
    result = await session.execute(
        select(KnowledgeBaseDocument).where(
            KnowledgeBaseDocument.id == document_id,
            KnowledgeBaseDocument.user_id == current_user.id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(doc, field, value)
    doc.updated_at = datetime.utcnow()

    await session.commit()
    await session.refresh(doc)
    return PastPerformanceRead.model_validate(doc)


@router.get("/documents/past-performances", response_model=PastPerformanceListResponse)
async def list_past_performances(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PastPerformanceListResponse:
    """List all past performance documents with metadata."""
    result = await session.execute(
        select(KnowledgeBaseDocument).where(
            KnowledgeBaseDocument.user_id == current_user.id,
            KnowledgeBaseDocument.document_type == DocumentType.PAST_PERFORMANCE,
        )
    )
    docs = result.scalars().all()
    data = [PastPerformanceRead.model_validate(d) for d in docs]
    return PastPerformanceListResponse(documents=data, total=len(data))


@router.post("/documents/past-performances/match/{rfp_id}", response_model=MatchResponse)
async def match_past_performance(
    rfp_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MatchResponse:
    """Match past performance documents against an RFP."""
    matches = await match_past_performances(session, rfp_id, current_user.id)
    return MatchResponse(
        rfp_id=rfp_id,
        matches=[
            MatchResult(
                document_id=m.document_id,
                title=m.title,
                score=m.score,
                matching_criteria=m.matching_criteria,
            )
            for m in matches
        ],
        total=len(matches),
    )


@router.post(
    "/documents/past-performances/{document_id}/narrative/{rfp_id}",
    response_model=NarrativeResponse,
)
async def generate_past_performance_narrative(
    document_id: int,
    rfp_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> NarrativeResponse:
    """Generate a tailored narrative for a past performance document."""
    narrative = await generate_narrative(session, document_id, rfp_id, current_user.id)
    if not narrative:
        raise HTTPException(status_code=404, detail="Document or RFP not found")
    return NarrativeResponse(
        document_id=document_id,
        rfp_id=rfp_id,
        narrative=narrative,
    )
