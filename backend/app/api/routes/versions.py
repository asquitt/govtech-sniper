"""
RFP Sniper - Version History Routes
====================================
API endpoints for proposal and section version history.
"""

from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from app.api.deps import UserAuth, get_current_user
from app.database import get_session
from app.models.proposal import (
    Proposal,
    ProposalSection,
    ProposalVersion,
    ProposalVersionType,
    SectionVersion,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/versions", tags=["Version History"])


# =============================================================================
# Response Schemas
# =============================================================================


class ProposalVersionResponse(BaseModel):
    """Response for proposal version."""

    id: int
    proposal_id: int
    version_number: int
    version_type: str
    description: str
    user_id: int
    created_at: datetime
    has_snapshot: bool


class SectionVersionResponse(BaseModel):
    """Response for section version."""

    id: int
    section_id: int
    version_number: int
    change_type: str
    change_summary: str | None
    word_count: int
    created_at: datetime


class VersionDetailResponse(BaseModel):
    """Detailed version with content."""

    id: int
    version_number: int
    change_type: str
    content: str
    word_count: int
    created_at: datetime
    diff_from_previous: str | None


class RestoreRequest(BaseModel):
    """Request to restore a version."""

    version_id: int


# =============================================================================
# Helper Functions
# =============================================================================


async def create_proposal_version(
    session: AsyncSession,
    proposal: Proposal,
    user_id: int,
    version_type: ProposalVersionType,
    description: str,
    section_id: int | None = None,
    section_snapshot: dict | None = None,
) -> ProposalVersion:
    """Create a new proposal version entry."""
    # Get current max version number
    result = await session.execute(
        select(func.max(ProposalVersion.version_number)).where(
            ProposalVersion.proposal_id == proposal.id
        )
    )
    max_version = result.scalar() or 0

    # Create snapshot
    snapshot = {
        "title": proposal.title,
        "status": proposal.status.value,
        "total_sections": proposal.total_sections,
        "completed_sections": proposal.completed_sections,
        "compliance_score": proposal.compliance_score,
    }

    version = ProposalVersion(
        proposal_id=proposal.id,
        user_id=user_id,
        version_number=max_version + 1,
        version_type=version_type,
        description=description,
        snapshot=snapshot,
        section_id=section_id,
        section_snapshot=section_snapshot,
    )

    session.add(version)
    return version


async def create_section_version(
    session: AsyncSession,
    section: ProposalSection,
    user_id: int,
    change_type: str,
    change_summary: str | None = None,
) -> SectionVersion:
    """Create a new section version entry."""
    # Get current max version number
    result = await session.execute(
        select(func.max(SectionVersion.version_number)).where(
            SectionVersion.section_id == section.id
        )
    )
    max_version = result.scalar() or 0

    # Get content
    content = section.final_content or ""
    if not content and section.generated_content:
        content = section.generated_content.get("clean_text", "")

    version = SectionVersion(
        section_id=section.id,
        user_id=user_id,
        version_number=max_version + 1,
        content=content,
        word_count=len(content.split()) if content else 0,
        change_type=change_type,
        change_summary=change_summary,
    )

    session.add(version)
    return version


# =============================================================================
# Proposal Version Endpoints
# =============================================================================


@router.get("/proposals/{proposal_id}", response_model=list[ProposalVersionResponse])
async def list_proposal_versions(
    proposal_id: int,
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ProposalVersionResponse]:
    """
    List all versions of a proposal.
    """
    # Verify proposal access
    proposal_result = await session.execute(
        select(Proposal).where(
            Proposal.id == proposal_id,
            Proposal.user_id == current_user.id,
        )
    )
    proposal = proposal_result.scalar_one_or_none()

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    # Get versions
    result = await session.execute(
        select(ProposalVersion)
        .where(ProposalVersion.proposal_id == proposal_id)
        .order_by(ProposalVersion.version_number.desc())
        .offset(offset)
        .limit(limit)
    )
    versions = result.scalars().all()

    return [
        ProposalVersionResponse(
            id=v.id,
            proposal_id=v.proposal_id,
            version_number=v.version_number,
            version_type=v.version_type.value,
            description=v.description,
            user_id=v.user_id,
            created_at=v.created_at,
            has_snapshot=bool(v.snapshot),
        )
        for v in versions
    ]


@router.get("/proposals/{proposal_id}/version/{version_id}")
async def get_proposal_version(
    proposal_id: int,
    version_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Get detailed proposal version with snapshot.
    """
    # Verify proposal access
    proposal_result = await session.execute(
        select(Proposal).where(
            Proposal.id == proposal_id,
            Proposal.user_id == current_user.id,
        )
    )
    proposal = proposal_result.scalar_one_or_none()

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    # Get version
    result = await session.execute(
        select(ProposalVersion).where(
            ProposalVersion.id == version_id,
            ProposalVersion.proposal_id == proposal_id,
        )
    )
    version = result.scalar_one_or_none()

    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    return {
        "id": version.id,
        "proposal_id": version.proposal_id,
        "version_number": version.version_number,
        "version_type": version.version_type.value,
        "description": version.description,
        "snapshot": version.snapshot,
        "section_id": version.section_id,
        "section_snapshot": version.section_snapshot,
        "created_at": version.created_at,
    }


# =============================================================================
# Section Version Endpoints
# =============================================================================


@router.get("/sections/{section_id}", response_model=list[SectionVersionResponse])
async def list_section_versions(
    section_id: int,
    limit: int = Query(50, le=100),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[SectionVersionResponse]:
    """
    List all versions of a proposal section.
    """
    # Verify section access
    section_result = await session.execute(
        select(ProposalSection)
        .join(Proposal)
        .where(
            ProposalSection.id == section_id,
            Proposal.user_id == current_user.id,
        )
    )
    section = section_result.scalar_one_or_none()

    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    # Get versions
    result = await session.execute(
        select(SectionVersion)
        .where(SectionVersion.section_id == section_id)
        .order_by(SectionVersion.version_number.desc())
        .limit(limit)
    )
    versions = result.scalars().all()

    return [
        SectionVersionResponse(
            id=v.id,
            section_id=v.section_id,
            version_number=v.version_number,
            change_type=v.change_type,
            change_summary=v.change_summary,
            word_count=v.word_count,
            created_at=v.created_at,
        )
        for v in versions
    ]


@router.get("/sections/{section_id}/version/{version_id}")
async def get_section_version(
    section_id: int,
    version_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> VersionDetailResponse:
    """
    Get detailed section version with content.
    """
    # Verify section access
    section_result = await session.execute(
        select(ProposalSection)
        .join(Proposal)
        .where(
            ProposalSection.id == section_id,
            Proposal.user_id == current_user.id,
        )
    )
    section = section_result.scalar_one_or_none()

    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    # Get version
    result = await session.execute(
        select(SectionVersion).where(
            SectionVersion.id == version_id,
            SectionVersion.section_id == section_id,
        )
    )
    version = result.scalar_one_or_none()

    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    return VersionDetailResponse(
        id=version.id,
        version_number=version.version_number,
        change_type=version.change_type,
        content=version.content,
        word_count=version.word_count,
        created_at=version.created_at,
        diff_from_previous=version.diff_from_previous,
    )


@router.post("/sections/{section_id}/restore")
async def restore_section_version(
    section_id: int,
    request: RestoreRequest,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Restore a section to a previous version.
    """
    # Verify section access
    section_result = await session.execute(
        select(ProposalSection)
        .join(Proposal)
        .where(
            ProposalSection.id == section_id,
            Proposal.user_id == current_user.id,
        )
    )
    section = section_result.scalar_one_or_none()

    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    # Get the version to restore
    version_result = await session.execute(
        select(SectionVersion).where(
            SectionVersion.id == request.version_id,
            SectionVersion.section_id == section_id,
        )
    )
    version = version_result.scalar_one_or_none()

    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    # Save current state first
    await create_section_version(
        session=session,
        section=section,
        user_id=current_user.id,
        change_type="before_restore",
        change_summary=f"State before restoring to version {version.version_number}",
    )

    # Restore content
    section.final_content = version.content
    section.word_count = version.word_count
    section.updated_at = datetime.utcnow()

    # Create restore version
    await create_section_version(
        session=session,
        section=section,
        user_id=current_user.id,
        change_type="restored",
        change_summary=f"Restored to version {version.version_number}",
    )

    # Also create proposal-level version
    proposal_result = await session.execute(
        select(Proposal).where(Proposal.id == section.proposal_id)
    )
    proposal = proposal_result.scalar_one()

    await create_proposal_version(
        session=session,
        proposal=proposal,
        user_id=current_user.id,
        version_type=ProposalVersionType.RESTORED,
        description=f"Section '{section.title}' restored to version {version.version_number}",
        section_id=section.id,
    )

    await session.commit()

    logger.info(
        "Section restored",
        section_id=section_id,
        restored_to_version=version.version_number,
    )

    return {
        "message": f"Restored to version {version.version_number}",
        "section_id": section_id,
        "restored_version": version.version_number,
    }


@router.get("/sections/{section_id}/compare")
async def compare_section_versions(
    section_id: int,
    version_a: int = Query(..., description="First version number"),
    version_b: int = Query(..., description="Second version number"),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Compare two versions of a section.
    Returns the content of both versions for diff display.
    """
    # Verify section access
    section_result = await session.execute(
        select(ProposalSection)
        .join(Proposal)
        .where(
            ProposalSection.id == section_id,
            Proposal.user_id == current_user.id,
        )
    )
    section = section_result.scalar_one_or_none()

    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    # Get both versions
    result = await session.execute(
        select(SectionVersion).where(
            SectionVersion.section_id == section_id,
            SectionVersion.version_number.in_([version_a, version_b]),
        )
    )
    versions = {v.version_number: v for v in result.scalars().all()}

    if version_a not in versions or version_b not in versions:
        raise HTTPException(status_code=404, detail="One or both versions not found")

    va = versions[version_a]
    vb = versions[version_b]

    return {
        "section_id": section_id,
        "version_a": {
            "version_number": va.version_number,
            "content": va.content,
            "word_count": va.word_count,
            "created_at": va.created_at,
        },
        "version_b": {
            "version_number": vb.version_number,
            "content": vb.content,
            "word_count": vb.word_count,
            "created_at": vb.created_at,
        },
    }
