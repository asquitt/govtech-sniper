"""
Draft Routes - Section Evidence CRUD
"""


from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user_optional, resolve_user_id
from app.database import get_session
from app.models.knowledge_base import DocumentChunk, KnowledgeBaseDocument
from app.models.proposal import Proposal, ProposalSection, SectionEvidence
from app.schemas.proposal import SectionEvidenceCreate, SectionEvidenceRead
from app.services.audit_service import log_audit_event
from app.services.auth_service import UserAuth
from app.services.webhook_service import dispatch_webhook_event

router = APIRouter()


@router.get("/sections/{section_id}/evidence", response_model=list[SectionEvidenceRead])
async def list_section_evidence(
    section_id: int,
    user_id: int | None = Query(None, description="User ID (optional if authenticated)"),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> list[SectionEvidenceRead]:
    """
    List evidence links for a section.
    """
    resolved_user_id = resolve_user_id(user_id, current_user)

    section_result = await session.execute(
        select(ProposalSection).where(ProposalSection.id == section_id)
    )
    section = section_result.scalar_one_or_none()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    proposal_result = await session.execute(
        select(Proposal).where(Proposal.id == section.proposal_id)
    )
    proposal = proposal_result.scalar_one_or_none()
    if not proposal or proposal.user_id != resolved_user_id:
        raise HTTPException(status_code=404, detail="Section not found")

    evidence_result = await session.execute(
        select(SectionEvidence).where(SectionEvidence.section_id == section_id)
    )
    evidence_links = evidence_result.scalars().all()

    response: list[SectionEvidenceRead] = []
    for link in evidence_links:
        doc_result = await session.execute(
            select(KnowledgeBaseDocument).where(KnowledgeBaseDocument.id == link.document_id)
        )
        doc = doc_result.scalar_one_or_none()
        response.append(
            SectionEvidenceRead(
                id=link.id,
                section_id=link.section_id,
                document_id=link.document_id,
                chunk_id=link.chunk_id,
                citation=link.citation,
                notes=link.notes,
                created_at=link.created_at,
                document_title=doc.title if doc else None,
                document_filename=doc.original_filename if doc else None,
            )
        )

    return response


@router.post("/sections/{section_id}/evidence", response_model=SectionEvidenceRead)
async def add_section_evidence(
    section_id: int,
    payload: SectionEvidenceCreate,
    user_id: int | None = Query(None, description="User ID (optional if authenticated)"),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> SectionEvidenceRead:
    """
    Add evidence link to a section.
    """
    resolved_user_id = resolve_user_id(user_id, current_user)

    section_result = await session.execute(
        select(ProposalSection).where(ProposalSection.id == section_id)
    )
    section = section_result.scalar_one_or_none()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    proposal_result = await session.execute(
        select(Proposal).where(Proposal.id == section.proposal_id)
    )
    proposal = proposal_result.scalar_one_or_none()
    if not proposal or proposal.user_id != resolved_user_id:
        raise HTTPException(status_code=404, detail="Section not found")

    document_result = await session.execute(
        select(KnowledgeBaseDocument).where(KnowledgeBaseDocument.id == payload.document_id)
    )
    document = document_result.scalar_one_or_none()
    if not document or document.user_id != resolved_user_id:
        raise HTTPException(status_code=404, detail="Document not found")

    if payload.chunk_id:
        chunk_result = await session.execute(
            select(DocumentChunk).where(
                DocumentChunk.id == payload.chunk_id,
                DocumentChunk.document_id == payload.document_id,
            )
        )
        if not chunk_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Document chunk not found")

    link = SectionEvidence(
        section_id=section_id,
        document_id=payload.document_id,
        chunk_id=payload.chunk_id,
        citation=payload.citation,
        notes=payload.notes,
    )
    session.add(link)
    await session.flush()

    await log_audit_event(
        session,
        user_id=resolved_user_id,
        entity_type="section_evidence",
        entity_id=link.id,
        action="proposal.section.evidence.added",
        metadata={
            "proposal_id": proposal.id,
            "section_id": section_id,
            "document_id": payload.document_id,
        },
    )
    await dispatch_webhook_event(
        session,
        user_id=resolved_user_id,
        event_type="proposal.section.evidence.added",
        payload={
            "proposal_id": proposal.id,
            "section_id": section_id,
            "document_id": payload.document_id,
        },
    )

    await session.commit()
    await session.refresh(link)

    return SectionEvidenceRead(
        id=link.id,
        section_id=link.section_id,
        document_id=link.document_id,
        chunk_id=link.chunk_id,
        citation=link.citation,
        notes=link.notes,
        created_at=link.created_at,
        document_title=document.title,
        document_filename=document.original_filename,
    )


@router.delete("/sections/{section_id}/evidence/{evidence_id}")
async def delete_section_evidence(
    section_id: int,
    evidence_id: int,
    user_id: int | None = Query(None, description="User ID (optional if authenticated)"),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Remove evidence link from a section.
    """
    resolved_user_id = resolve_user_id(user_id, current_user)

    section_result = await session.execute(
        select(ProposalSection).where(ProposalSection.id == section_id)
    )
    section = section_result.scalar_one_or_none()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    proposal_result = await session.execute(
        select(Proposal).where(Proposal.id == section.proposal_id)
    )
    proposal = proposal_result.scalar_one_or_none()
    if not proposal or proposal.user_id != resolved_user_id:
        raise HTTPException(status_code=404, detail="Section not found")

    evidence_result = await session.execute(
        select(SectionEvidence).where(
            SectionEvidence.id == evidence_id,
            SectionEvidence.section_id == section_id,
        )
    )
    evidence = evidence_result.scalar_one_or_none()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence link not found")

    await session.delete(evidence)

    await log_audit_event(
        session,
        user_id=resolved_user_id,
        entity_type="section_evidence",
        entity_id=evidence_id,
        action="proposal.section.evidence.deleted",
        metadata={"section_id": section_id, "proposal_id": proposal.id},
    )
    await dispatch_webhook_event(
        session,
        user_id=resolved_user_id,
        event_type="proposal.section.evidence.deleted",
        payload={"section_id": section_id, "proposal_id": proposal.id},
    )

    await session.commit()

    return {"message": "Evidence deleted", "evidence_id": evidence_id}
