"""
Outline Routes
==============
Generate and manage structured proposal outlines.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from kombu.exceptions import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import UserAuth, get_current_user_optional, resolve_user_id
from app.config import settings
from app.database import get_session
from app.models.outline import OutlineSection, OutlineStatus, ProposalOutline
from app.models.proposal import Proposal, ProposalSection, SectionStatus
from app.schemas.outline import (
    OutlineRead,
    OutlineReorderRequest,
    OutlineSectionCreate,
    OutlineSectionRead,
    OutlineSectionUpdate,
)

router = APIRouter()


def _build_tree(sections: list, parent_id: int | None = None) -> list[OutlineSectionRead]:
    """Build nested tree from flat sections list."""
    tree = []
    for s in sections:
        if s.parent_id == parent_id:
            node = OutlineSectionRead(
                id=s.id,
                outline_id=s.outline_id,
                parent_id=s.parent_id,
                title=s.title,
                description=s.description,
                mapped_requirement_ids=s.mapped_requirement_ids or [],
                display_order=s.display_order,
                estimated_pages=s.estimated_pages,
                created_at=s.created_at,
                updated_at=s.updated_at,
                children=_build_tree(sections, parent_id=s.id),
            )
            tree.append(node)
    tree.sort(key=lambda x: x.display_order)
    return tree


async def _get_outline_or_404(
    proposal_id: int,
    user_id: int,
    session: AsyncSession,
) -> tuple:
    """Get proposal and outline, raising 404 if not found."""
    proposal_result = await session.execute(select(Proposal).where(Proposal.id == proposal_id))
    proposal = proposal_result.scalar_one_or_none()
    if not proposal or proposal.user_id != user_id:
        raise HTTPException(status_code=404, detail="Proposal not found")

    outline_result = await session.execute(
        select(ProposalOutline).where(ProposalOutline.proposal_id == proposal_id)
    )
    outline = outline_result.scalar_one_or_none()
    return proposal, outline


async def _run_outline_generation_sync(
    *,
    proposal_id: int,
    resolved_user_id: int,
    session: AsyncSession,
) -> dict:
    """
    Execute outline generation synchronously in local/mock environments where no
    Celery worker is available.
    """
    from app.tasks.generation_tasks import generate_proposal_outline_async

    sync_task_id = f"sync-outline-{proposal_id}-{int(datetime.utcnow().timestamp())}"
    sync_result = await generate_proposal_outline_async(
        proposal_id=proposal_id,
        user_id=resolved_user_id,
        task_id=sync_task_id,
        session_override=session,
    )
    payload = sync_result if isinstance(sync_result, dict) else {}
    status = payload.get("status", "completed")
    message = (
        "Outline generation completed synchronously."
        if status == "completed"
        else "Outline generation executed synchronously."
    )

    return {
        "task_id": sync_task_id,
        "message": message,
        "status": status,
    }


@router.post("/proposals/{proposal_id}/generate-outline")
async def generate_outline(
    proposal_id: int,
    user_id: int | None = Query(None),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Trigger AI outline generation from compliance matrix."""
    resolved_user_id = resolve_user_id(user_id, current_user)

    await _get_outline_or_404(proposal_id, resolved_user_id, session)

    from app.api.routes.draft.generation import _celery_broker_available, _celery_worker_available
    from app.tasks.generation_tasks import generate_proposal_outline

    # Keep outline generation deterministic in local/dev when broker or worker is unavailable.
    should_fallback_sync = (settings.debug or settings.mock_ai) and (
        not _celery_broker_available() or not _celery_worker_available()
    )
    if should_fallback_sync:
        return await _run_outline_generation_sync(
            proposal_id=proposal_id,
            resolved_user_id=resolved_user_id,
            session=session,
        )

    try:
        task = generate_proposal_outline.delay(
            proposal_id=proposal_id,
            user_id=resolved_user_id,
        )
    except OperationalError as exc:
        if settings.debug or settings.mock_ai:
            return await _run_outline_generation_sync(
                proposal_id=proposal_id,
                resolved_user_id=resolved_user_id,
                session=session,
            )
        raise HTTPException(
            status_code=503,
            detail="Outline generation worker unavailable. Please try again shortly.",
        ) from exc

    return {"task_id": task.id, "message": "Outline generation started", "status": "generating"}


@router.get("/proposals/{proposal_id}/outline", response_model=OutlineRead)
async def get_outline(
    proposal_id: int,
    user_id: int | None = Query(None),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> OutlineRead:
    """Get the proposal outline with nested sections."""
    resolved_user_id = resolve_user_id(user_id, current_user)
    _, outline = await _get_outline_or_404(proposal_id, resolved_user_id, session)

    if not outline:
        raise HTTPException(status_code=404, detail="No outline generated yet")

    sections_result = await session.execute(
        select(OutlineSection)
        .where(OutlineSection.outline_id == outline.id)
        .order_by(OutlineSection.display_order)
    )
    all_sections = sections_result.scalars().all()
    tree = _build_tree(all_sections)

    return OutlineRead(
        id=outline.id,
        proposal_id=outline.proposal_id,
        status=outline.status,
        created_at=outline.created_at,
        updated_at=outline.updated_at,
        sections=tree,
    )


@router.post(
    "/proposals/{proposal_id}/outline/sections",
    response_model=OutlineSectionRead,
)
async def add_outline_section(
    proposal_id: int,
    body: OutlineSectionCreate,
    user_id: int | None = Query(None),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> OutlineSectionRead:
    """Add a manual section to the outline."""
    resolved_user_id = resolve_user_id(user_id, current_user)
    _, outline = await _get_outline_or_404(proposal_id, resolved_user_id, session)

    if not outline:
        raise HTTPException(status_code=404, detail="No outline generated yet")

    section = OutlineSection(
        outline_id=outline.id,
        parent_id=body.parent_id,
        title=body.title,
        description=body.description,
        mapped_requirement_ids=body.mapped_requirement_ids,
        display_order=body.display_order,
        estimated_pages=body.estimated_pages,
    )
    session.add(section)
    await session.commit()
    await session.refresh(section)

    return OutlineSectionRead(
        id=section.id,
        outline_id=section.outline_id,
        parent_id=section.parent_id,
        title=section.title,
        description=section.description,
        mapped_requirement_ids=section.mapped_requirement_ids or [],
        display_order=section.display_order,
        estimated_pages=section.estimated_pages,
        created_at=section.created_at,
        updated_at=section.updated_at,
        children=[],
    )


@router.patch("/proposals/{proposal_id}/outline/sections/{section_id}")
async def update_outline_section(
    proposal_id: int,
    section_id: int,
    body: OutlineSectionUpdate,
    user_id: int | None = Query(None),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> OutlineSectionRead:
    """Edit an outline section."""
    resolved_user_id = resolve_user_id(user_id, current_user)
    _, outline = await _get_outline_or_404(proposal_id, resolved_user_id, session)

    if not outline:
        raise HTTPException(status_code=404, detail="No outline")

    section_result = await session.execute(
        select(OutlineSection).where(
            OutlineSection.id == section_id,
            OutlineSection.outline_id == outline.id,
        )
    )
    section = section_result.scalar_one_or_none()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(section, field, value)
    section.updated_at = datetime.utcnow()

    await session.commit()
    await session.refresh(section)

    return OutlineSectionRead(
        id=section.id,
        outline_id=section.outline_id,
        parent_id=section.parent_id,
        title=section.title,
        description=section.description,
        mapped_requirement_ids=section.mapped_requirement_ids or [],
        display_order=section.display_order,
        estimated_pages=section.estimated_pages,
        created_at=section.created_at,
        updated_at=section.updated_at,
        children=[],
    )


@router.delete("/proposals/{proposal_id}/outline/sections/{section_id}")
async def delete_outline_section(
    proposal_id: int,
    section_id: int,
    user_id: int | None = Query(None),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Delete an outline section and its children."""
    resolved_user_id = resolve_user_id(user_id, current_user)
    _, outline = await _get_outline_or_404(proposal_id, resolved_user_id, session)

    if not outline:
        raise HTTPException(status_code=404, detail="No outline")

    section_result = await session.execute(
        select(OutlineSection).where(
            OutlineSection.id == section_id,
            OutlineSection.outline_id == outline.id,
        )
    )
    section = section_result.scalar_one_or_none()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    # Delete children first
    children_result = await session.execute(
        select(OutlineSection).where(OutlineSection.parent_id == section_id)
    )
    for child in children_result.scalars().all():
        await session.delete(child)

    await session.delete(section)
    await session.commit()

    return {"message": "Section deleted", "section_id": section_id}


@router.put("/proposals/{proposal_id}/outline/reorder")
async def reorder_outline(
    proposal_id: int,
    body: OutlineReorderRequest,
    user_id: int | None = Query(None),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Reorder outline sections."""
    resolved_user_id = resolve_user_id(user_id, current_user)
    _, outline = await _get_outline_or_404(proposal_id, resolved_user_id, session)

    if not outline:
        raise HTTPException(status_code=404, detail="No outline")

    for item in body.items:
        section_result = await session.execute(
            select(OutlineSection).where(
                OutlineSection.id == item.section_id,
                OutlineSection.outline_id == outline.id,
            )
        )
        section = section_result.scalar_one_or_none()
        if section:
            section.parent_id = item.parent_id
            section.display_order = item.display_order
            section.updated_at = datetime.utcnow()

    await session.commit()
    return {"message": "Outline reordered", "sections_updated": len(body.items)}


@router.post("/proposals/{proposal_id}/outline/approve")
async def approve_outline(
    proposal_id: int,
    user_id: int | None = Query(None),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Approve outline and auto-create ProposalSections from it."""
    resolved_user_id = resolve_user_id(user_id, current_user)
    _, outline = await _get_outline_or_404(proposal_id, resolved_user_id, session)

    if not outline:
        raise HTTPException(status_code=404, detail="No outline")

    outline.status = OutlineStatus.APPROVED
    outline.updated_at = datetime.utcnow()

    # Get all outline sections (flat)
    sections_result = await session.execute(
        select(OutlineSection)
        .where(OutlineSection.outline_id == outline.id)
        .order_by(OutlineSection.display_order)
    )
    outline_sections = sections_result.scalars().all()

    # Create ProposalSections for leaf nodes (no children)
    parent_ids = {s.parent_id for s in outline_sections if s.parent_id is not None}
    sections_created = 0

    for i, os in enumerate(outline_sections):
        # Only create proposal sections for leaf nodes
        if os.id in parent_ids:
            continue

        # Build section number from display order
        section_number = f"{i + 1}"

        # Combine mapped requirement IDs into requirement text
        req_text = ", ".join(os.mapped_requirement_ids) if os.mapped_requirement_ids else None

        proposal_section = ProposalSection(
            proposal_id=proposal_id,
            title=os.title,
            section_number=section_number,
            requirement_id=os.mapped_requirement_ids[0] if os.mapped_requirement_ids else None,
            requirement_text=os.description or req_text,
            status=SectionStatus.PENDING,
            display_order=i,
        )
        session.add(proposal_section)
        sections_created += 1

    # Update proposal section counts
    proposal_result = await session.execute(select(Proposal).where(Proposal.id == proposal_id))
    proposal = proposal_result.scalar_one_or_none()
    if proposal:
        proposal.total_sections = (proposal.total_sections or 0) + sections_created

    await session.commit()

    return {
        "message": "Outline approved",
        "sections_created": sections_created,
        "outline_id": outline.id,
    }
