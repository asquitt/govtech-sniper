"""
Draft Routes - Section CRUD
"""

from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc
from sqlmodel import select, func

from app.database import get_session
from app.api.deps import get_current_user_optional, resolve_user_id
from app.services.auth_service import UserAuth
from app.models.proposal import (
    Proposal,
    ProposalSection,
    SectionStatus,
    ProposalVersion,
    ProposalVersionType,
    SectionVersion,
)
from app.models.rfp import ComplianceMatrix
from app.schemas.proposal import (
    ProposalSectionCreate,
    ProposalSectionRead,
    ProposalSectionUpdate,
)
from app.services.audit_service import log_audit_event
from app.services.webhook_service import dispatch_webhook_event

router = APIRouter()


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


@router.get("/proposals/{proposal_id}/sections", response_model=List[ProposalSectionRead])
async def list_sections(
    proposal_id: int,
    user_id: Optional[int] = Query(None, description="User ID (optional if authenticated)"),
    status: Optional[SectionStatus] = Query(None, description="Filter by section status"),
    current_user: Optional[UserAuth] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> List[ProposalSectionRead]:
    """
    List proposal sections.
    """
    resolved_user_id = resolve_user_id(user_id, current_user)

    proposal_result = await session.execute(
        select(Proposal).where(Proposal.id == proposal_id)
    )
    proposal = proposal_result.scalar_one_or_none()
    if not proposal or proposal.user_id != resolved_user_id:
        raise HTTPException(status_code=404, detail="Proposal not found")

    query = select(ProposalSection).where(ProposalSection.proposal_id == proposal_id)
    if status:
        query = query.where(ProposalSection.status == status)

    result = await session.execute(query.order_by(ProposalSection.display_order))
    sections = result.scalars().all()
    return [ProposalSectionRead.model_validate(section) for section in sections]


@router.get("/sections/{section_id}", response_model=ProposalSectionRead)
async def get_section(
    section_id: int,
    user_id: Optional[int] = Query(None, description="User ID (optional if authenticated)"),
    current_user: Optional[UserAuth] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> ProposalSectionRead:
    """
    Get a proposal section by id.
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

    return ProposalSectionRead.model_validate(section)


@router.patch("/sections/{section_id}", response_model=ProposalSectionRead)
async def update_section(
    section_id: int,
    update: ProposalSectionUpdate,
    user_id: Optional[int] = Query(None, description="User ID (optional if authenticated)"),
    current_user: Optional[UserAuth] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> ProposalSectionRead:
    """
    Update a proposal section (final content, status, metadata).
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

    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(section, field, value)

    if "final_content" in update_data and update_data.get("final_content"):
        section.word_count = len(update_data["final_content"].split())
        if "status" not in update_data:
            section.status = SectionStatus.EDITING

    section.updated_at = datetime.utcnow()

    # Update compliance matrix addressed status if mapped to requirement
    if section.requirement_id:
        matrix_result = await session.execute(
            select(ComplianceMatrix).where(ComplianceMatrix.rfp_id == proposal.rfp_id)
        )
        matrix = matrix_result.scalar_one_or_none()
        if matrix:
            for req in matrix.requirements:
                if req.get("id") == section.requirement_id:
                    if update_data.get("status") == SectionStatus.APPROVED:
                        req["is_addressed"] = True
                    elif "final_content" in update_data and update_data.get("final_content"):
                        req["is_addressed"] = True
                    elif update_data.get("status") == SectionStatus.PENDING:
                        req["is_addressed"] = False
                    break
            # Recalculate counts
            matrix.total_requirements = len(matrix.requirements)
            matrix.mandatory_count = len(
                [r for r in matrix.requirements if r.get("importance") == "mandatory"]
            )
            matrix.addressed_count = len(
                [r for r in matrix.requirements if r.get("is_addressed")]
            )
            matrix.updated_at = datetime.utcnow()

    # Update proposal completion counts
    completed_result = await session.execute(
        select(ProposalSection).where(
            ProposalSection.proposal_id == proposal.id,
            ProposalSection.status.in_([
                SectionStatus.GENERATED,
                SectionStatus.APPROVED,
            ]),
        )
    )
    proposal.completed_sections = len(completed_result.scalars().all())
    proposal.updated_at = datetime.utcnow()

    # Version tracking
    if "final_content" in update_data or "status" in update_data:
        max_version_result = await session.execute(
            select(func.max(SectionVersion.version_number)).where(
                SectionVersion.section_id == section.id
            )
        )
        max_version = max_version_result.scalar() or 0
        section_version = SectionVersion(
            section_id=section.id,
            user_id=resolved_user_id,
            version_number=max_version + 1,
            content=section.final_content or "",
            word_count=section.word_count or 0,
            change_type="edited" if "final_content" in update_data else "status_change",
            change_summary="Section updated",
        )
        session.add(section_version)

        proposal_max_result = await session.execute(
            select(func.max(ProposalVersion.version_number)).where(
                ProposalVersion.proposal_id == proposal.id
            )
        )
        proposal_max = proposal_max_result.scalar() or 0
        proposal_version = ProposalVersion(
            proposal_id=proposal.id,
            user_id=resolved_user_id,
            version_number=proposal_max + 1,
            version_type=ProposalVersionType.SECTION_EDITED,
            description=f"Updated section {section.section_number}",
            snapshot={
                "title": proposal.title,
                "status": proposal.status.value,
                "total_sections": proposal.total_sections,
                "completed_sections": proposal.completed_sections,
                "compliance_score": proposal.compliance_score,
            },
            section_id=section.id,
            section_snapshot={
                "section_id": section.id,
                "title": section.title,
                "status": section.status.value,
            },
        )
        session.add(proposal_version)

    await log_audit_event(
        session,
        user_id=resolved_user_id,
        entity_type="proposal_section",
        entity_id=section.id,
        action="proposal.section.updated",
        metadata={"proposal_id": proposal.id, "section_id": section.id},
    )
    await dispatch_webhook_event(
        session,
        user_id=resolved_user_id,
        event_type="proposal.section.updated",
        payload={"proposal_id": proposal.id, "section_id": section.id},
    )

    await session.commit()
    await session.refresh(section)

    return ProposalSectionRead.model_validate(section)
