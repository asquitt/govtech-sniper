"""
RFP Sniper - Draft Generation Routes
=====================================
Endpoints for proposal section generation with RAG.
"""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc
from sqlmodel import select

from app.database import get_session
from app.api.deps import get_current_user_optional, resolve_user_id
from app.services.auth_service import UserAuth
from app.models.proposal import Proposal, ProposalSection, SectionStatus
from app.models.rfp import RFP, ComplianceMatrix
from app.schemas.proposal import (
    DraftRequest,
    DraftResponse,
    ProposalCreate,
    ProposalRead,
    ProposalSectionCreate,
    ProposalSectionRead,
)
from app.tasks.generation_tasks import (
    generate_proposal_section,
    generate_all_sections,
    refresh_context_cache,
)
from app.config import settings

router = APIRouter(prefix="/draft", tags=["Draft Generation"])


@router.post("/proposals", response_model=ProposalRead)
async def create_proposal(
    proposal: ProposalCreate,
    user_id: Optional[int] = Query(None, description="User ID (optional if authenticated)"),
    current_user: Optional[UserAuth] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> ProposalRead:
    """
    Create a new proposal for an RFP.
    
    This initializes the proposal structure. Use the sections
    endpoints to add content.
    """
    # Verify RFP exists
    result = await session.execute(
        select(RFP).where(RFP.id == proposal.rfp_id)
    )
    rfp = result.scalar_one_or_none()
    
    if not rfp:
        raise HTTPException(status_code=404, detail=f"RFP {proposal.rfp_id} not found")
    
    resolved_user_id = resolve_user_id(user_id, current_user)

    # Create proposal
    new_proposal = Proposal(
        user_id=resolved_user_id,
        rfp_id=proposal.rfp_id,
        title=proposal.title,
    )
    session.add(new_proposal)
    await session.commit()
    await session.refresh(new_proposal)
    
    return ProposalRead.from_orm_with_completion(new_proposal)


@router.post("/proposals/{proposal_id}/sections", response_model=ProposalSectionRead)
async def create_section(
    proposal_id: int,
    section: ProposalSectionCreate,
    session: AsyncSession = Depends(get_session),
) -> ProposalSectionRead:
    """
    Add a section to a proposal.
    
    Sections can be created manually or auto-generated from
    the compliance matrix.
    """
    # Verify proposal exists
    result = await session.execute(
        select(Proposal).where(Proposal.id == proposal_id)
    )
    proposal = result.scalar_one_or_none()
    
    if not proposal:
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found")
    
    # Create section
    new_section = ProposalSection(
        proposal_id=proposal_id,
        title=section.title,
        section_number=section.section_number,
        requirement_id=section.requirement_id,
        requirement_text=section.requirement_text,
        display_order=section.display_order,
    )
    session.add(new_section)
    
    # Update proposal section count
    proposal.total_sections += 1
    
    await session.commit()
    await session.refresh(new_section)
    
    return ProposalSectionRead.model_validate(new_section)


@router.post("/proposals/{proposal_id}/generate-from-matrix")
async def generate_sections_from_matrix(
    proposal_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Auto-generate proposal sections from the RFP's compliance matrix.
    
    Creates a section for each mandatory and evaluated requirement.
    """
    # Get proposal and RFP
    result = await session.execute(
        select(Proposal).where(Proposal.id == proposal_id)
    )
    proposal = result.scalar_one_or_none()
    
    if not proposal:
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found")
    
    # Get compliance matrix
    matrix_result = await session.execute(
        select(ComplianceMatrix).where(ComplianceMatrix.rfp_id == proposal.rfp_id)
    )
    matrix = matrix_result.scalar_one_or_none()
    
    if not matrix:
        raise HTTPException(
            status_code=400,
            detail="RFP has no compliance matrix. Run analysis first.",
        )
    
    # Create sections for each requirement
    sections_created = 0
    for i, req in enumerate(matrix.requirements):
        section = ProposalSection(
            proposal_id=proposal_id,
            title=f"Response to {req.get('section', 'Requirement')}",
            section_number=f"R{i+1:03d}",
            requirement_id=req.get("id"),
            requirement_text=req.get("requirement_text"),
            display_order=i,
        )
        session.add(section)
        sections_created += 1
    
    proposal.total_sections = sections_created
    await session.commit()
    
    return {
        "proposal_id": proposal_id,
        "sections_created": sections_created,
        "message": f"Created {sections_created} sections from compliance matrix",
    }


@router.post("/{requirement_id}", response_model=DraftResponse)
async def generate_section_draft(
    requirement_id: str = Path(..., description="Requirement ID from compliance matrix"),
    request: DraftRequest = None,
    user_id: Optional[int] = Query(None, description="User ID (optional if authenticated)"),
    current_user: Optional[UserAuth] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> DraftResponse:
    """
    Generate a draft response for a specific requirement.
    
    This is the core RAG endpoint that:
    1. Retrieves the user's Knowledge Base documents
    2. Uses Gemini 1.5 Pro's context caching for efficient lookups
    3. Generates compliant text with source citations
    
    **Citation Format:** Generated text includes [[Source: filename.pdf, Page XX]] markers.
    """
    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=503,
            detail="Gemini API key not configured",
        )
    
    # Parse request
    if request is None:
        request = DraftRequest(requirement_id=requirement_id)
    
    resolved_user_id = resolve_user_id(user_id, current_user)

    # Find the section for this requirement that belongs to the requesting user
    result = await session.execute(
        select(ProposalSection)
        .join(Proposal, ProposalSection.proposal_id == Proposal.id)
        .where(
            ProposalSection.requirement_id == requirement_id,
            Proposal.user_id == resolved_user_id,
        )
        .order_by(desc(ProposalSection.created_at))
        .limit(1)
    )
    section = result.scalar_one_or_none()
    
    if not section:
        raise HTTPException(
            status_code=404,
            detail=f"No section found for requirement {requirement_id}. Create proposal sections first.",
        )
    
    resolved_user_id = resolve_user_id(user_id, current_user)

    # Queue generation task
    task = generate_proposal_section.delay(
        section_id=section.id,
        user_id=resolved_user_id,
        max_words=request.max_words,
        tone=request.tone,
        additional_context=request.additional_context,
    )
    
    return DraftResponse(
        task_id=task.id,
        requirement_id=requirement_id,
        section_id=section.id,
        message="Draft generation started",
        status="generating",
    )


@router.post("/proposals/{proposal_id}/generate-all")
async def generate_all_proposal_sections(
    proposal_id: int,
    user_id: Optional[int] = Query(None, description="User ID (optional if authenticated)"),
    max_words: int = Query(500, ge=100, le=2000),
    tone: str = Query("professional", pattern="^(professional|technical|executive)$"),
    current_user: Optional[UserAuth] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Generate all pending sections for a proposal.
    
    Queues generation tasks for each section that hasn't been written yet.
    """
    if not settings.gemini_api_key:
        raise HTTPException(status_code=503, detail="Gemini API key not configured")
    
    # Verify proposal exists
    result = await session.execute(
        select(Proposal).where(Proposal.id == proposal_id)
    )
    proposal = result.scalar_one_or_none()
    
    if not proposal:
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found")
    
    resolved_user_id = resolve_user_id(user_id, current_user)

    # Queue batch generation
    task = generate_all_sections.delay(
        proposal_id=proposal_id,
        user_id=resolved_user_id,
        max_words_per_section=max_words,
        tone=tone,
    )
    
    return {
        "task_id": task.id,
        "proposal_id": proposal_id,
        "message": "Batch generation queued",
        "status": "processing",
    }


@router.post("/refresh-cache")
async def trigger_cache_refresh(
    user_id: Optional[int] = Query(None, description="User ID (optional if authenticated)"),
    ttl_hours: int = Query(24, ge=1, le=168, description="Cache TTL in hours"),
    current_user: Optional[UserAuth] = Depends(get_current_user_optional),
) -> dict:
    """
    Refresh the Gemini context cache for a user's Knowledge Base.
    
    Call this after uploading new documents to ensure they're included
    in the AI's context during generation.
    """
    resolved_user_id = resolve_user_id(user_id, current_user)

    task = refresh_context_cache.delay(
        user_id=resolved_user_id,
        ttl_hours=ttl_hours,
    )
    
    return {
        "task_id": task.id,
        "message": "Cache refresh started",
        "ttl_hours": ttl_hours,
    }


@router.get("/{task_id}/status")
async def get_generation_status(task_id: str) -> dict:
    """
    Get the status of a generation task.
    """
    from celery.result import AsyncResult
    from app.tasks.celery_app import celery_app
    
    def normalize_status(result: AsyncResult) -> str:
        if result.ready():
            return "completed" if result.successful() else "failed"
        state = (result.state or "").lower()
        if state in {"pending", "received"}:
            return "pending"
        return "processing"
    
    result = AsyncResult(task_id, app=celery_app)
    
    if result.ready():
        if result.successful():
            return {
                "task_id": task_id,
                "status": "completed",
                "result": result.get(),
            }
        else:
            return {
                "task_id": task_id,
                "status": "failed",
                "error": str(result.result),
            }
    else:
        return {
            "task_id": task_id,
            "status": normalize_status(result),
        }
