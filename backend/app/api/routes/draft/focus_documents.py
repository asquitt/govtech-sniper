"""
Focus Document Routes
=====================
Manage which knowledge base documents are used for proposal generation.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import UserAuth, get_current_user_optional, resolve_user_id
from app.database import get_session
from app.models.knowledge_base import KnowledgeBaseDocument
from app.models.proposal import Proposal
from app.models.proposal_focus_document import ProposalFocusDocument

router = APIRouter()


class FocusDocumentRead(BaseModel):
    id: int
    proposal_id: int
    document_id: int
    priority_order: int
    created_at: datetime
    document_title: str | None = None
    document_filename: str | None = None

    model_config = {"from_attributes": True}


class FocusDocumentsBulkSet(BaseModel):
    document_ids: list[int]


@router.get(
    "/proposals/{proposal_id}/focus-documents",
    response_model=list[FocusDocumentRead],
)
async def list_focus_documents(
    proposal_id: int,
    user_id: int | None = Query(None),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> list[FocusDocumentRead]:
    """List focus documents for a proposal."""
    resolved_user_id = resolve_user_id(user_id, current_user)

    proposal_result = await session.execute(select(Proposal).where(Proposal.id == proposal_id))
    proposal = proposal_result.scalar_one_or_none()
    if not proposal or proposal.user_id != resolved_user_id:
        raise HTTPException(status_code=404, detail="Proposal not found")

    result = await session.execute(
        select(ProposalFocusDocument)
        .where(ProposalFocusDocument.proposal_id == proposal_id)
        .order_by(ProposalFocusDocument.priority_order)
    )
    focus_docs = result.scalars().all()

    # Enrich with document metadata
    items: list[FocusDocumentRead] = []
    for fd in focus_docs:
        doc_result = await session.execute(
            select(KnowledgeBaseDocument).where(KnowledgeBaseDocument.id == fd.document_id)
        )
        doc = doc_result.scalar_one_or_none()
        items.append(
            FocusDocumentRead(
                id=fd.id,
                proposal_id=fd.proposal_id,
                document_id=fd.document_id,
                priority_order=fd.priority_order,
                created_at=fd.created_at,
                document_title=doc.title if doc else None,
                document_filename=doc.original_filename if doc else None,
            )
        )
    return items


@router.put(
    "/proposals/{proposal_id}/focus-documents",
    response_model=list[FocusDocumentRead],
)
async def set_focus_documents(
    proposal_id: int,
    body: FocusDocumentsBulkSet,
    user_id: int | None = Query(None),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> list[FocusDocumentRead]:
    """Bulk set focus documents for a proposal (replaces existing)."""
    resolved_user_id = resolve_user_id(user_id, current_user)

    proposal_result = await session.execute(select(Proposal).where(Proposal.id == proposal_id))
    proposal = proposal_result.scalar_one_or_none()
    if not proposal or proposal.user_id != resolved_user_id:
        raise HTTPException(status_code=404, detail="Proposal not found")

    # Delete existing focus docs
    existing = await session.execute(
        select(ProposalFocusDocument).where(ProposalFocusDocument.proposal_id == proposal_id)
    )
    for fd in existing.scalars().all():
        await session.delete(fd)

    # Create new focus docs
    items: list[FocusDocumentRead] = []
    for i, doc_id in enumerate(body.document_ids):
        # Verify document belongs to user
        doc_result = await session.execute(
            select(KnowledgeBaseDocument).where(
                KnowledgeBaseDocument.id == doc_id,
                KnowledgeBaseDocument.user_id == resolved_user_id,
            )
        )
        doc = doc_result.scalar_one_or_none()
        if not doc:
            continue

        fd = ProposalFocusDocument(
            proposal_id=proposal_id,
            document_id=doc_id,
            priority_order=i,
        )
        session.add(fd)
        await session.flush()

        items.append(
            FocusDocumentRead(
                id=fd.id,
                proposal_id=fd.proposal_id,
                document_id=fd.document_id,
                priority_order=fd.priority_order,
                created_at=fd.created_at,
                document_title=doc.title,
                document_filename=doc.original_filename,
            )
        )

    await session.commit()
    return items


@router.delete(
    "/proposals/{proposal_id}/focus-documents/{document_id}",
)
async def remove_focus_document(
    proposal_id: int,
    document_id: int,
    user_id: int | None = Query(None),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Remove a single focus document from a proposal."""
    resolved_user_id = resolve_user_id(user_id, current_user)

    proposal_result = await session.execute(select(Proposal).where(Proposal.id == proposal_id))
    proposal = proposal_result.scalar_one_or_none()
    if not proposal or proposal.user_id != resolved_user_id:
        raise HTTPException(status_code=404, detail="Proposal not found")

    result = await session.execute(
        select(ProposalFocusDocument).where(
            ProposalFocusDocument.proposal_id == proposal_id,
            ProposalFocusDocument.document_id == document_id,
        )
    )
    fd = result.scalar_one_or_none()
    if not fd:
        raise HTTPException(status_code=404, detail="Focus document not found")

    await session.delete(fd)
    await session.commit()

    return {"message": "Focus document removed", "document_id": document_id}
