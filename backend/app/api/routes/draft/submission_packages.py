"""
Draft Routes - Submission Package CRUD
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user_optional, resolve_user_id
from app.database import get_session
from app.models.proposal import (
    Proposal,
    SubmissionPackage,
    SubmissionPackageStatus,
)
from app.schemas.proposal import (
    SubmissionPackageCreate,
    SubmissionPackageRead,
    SubmissionPackageUpdate,
)
from app.services.audit_service import log_audit_event
from app.services.auth_service import UserAuth
from app.services.webhook_service import dispatch_webhook_event

router = APIRouter()


@router.get(
    "/proposals/{proposal_id}/submission-packages", response_model=list[SubmissionPackageRead]
)
async def list_submission_packages(
    proposal_id: int,
    user_id: int | None = Query(None, description="User ID (optional if authenticated)"),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> list[SubmissionPackageRead]:
    """
    List submission packages for a proposal.
    """
    resolved_user_id = resolve_user_id(user_id, current_user)

    proposal_result = await session.execute(select(Proposal).where(Proposal.id == proposal_id))
    proposal = proposal_result.scalar_one_or_none()
    if not proposal or proposal.user_id != resolved_user_id:
        raise HTTPException(status_code=404, detail="Proposal not found")

    result = await session.execute(
        select(SubmissionPackage)
        .where(SubmissionPackage.proposal_id == proposal_id)
        .order_by(SubmissionPackage.created_at.desc())
    )
    packages = result.scalars().all()
    return [SubmissionPackageRead.model_validate(pkg) for pkg in packages]


@router.post("/proposals/{proposal_id}/submission-packages", response_model=SubmissionPackageRead)
async def create_submission_package(
    proposal_id: int,
    payload: SubmissionPackageCreate,
    user_id: int | None = Query(None, description="User ID (optional if authenticated)"),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> SubmissionPackageRead:
    """
    Create a submission package for a proposal.
    """
    resolved_user_id = resolve_user_id(user_id, current_user)

    proposal_result = await session.execute(select(Proposal).where(Proposal.id == proposal_id))
    proposal = proposal_result.scalar_one_or_none()
    if not proposal or proposal.user_id != resolved_user_id:
        raise HTTPException(status_code=404, detail="Proposal not found")

    package = SubmissionPackage(
        proposal_id=proposal_id,
        owner_id=payload.owner_id,
        title=payload.title,
        due_date=payload.due_date,
        checklist=payload.checklist or [],
        notes=payload.notes,
    )
    session.add(package)
    await session.flush()

    await log_audit_event(
        session,
        user_id=resolved_user_id,
        entity_type="submission_package",
        entity_id=package.id,
        action="proposal.submission_package.created",
        metadata={"proposal_id": proposal_id, "title": payload.title},
    )
    await dispatch_webhook_event(
        session,
        user_id=resolved_user_id,
        event_type="proposal.submission_package.created",
        payload={"proposal_id": proposal_id, "title": payload.title},
    )

    await session.commit()
    await session.refresh(package)

    return SubmissionPackageRead.model_validate(package)


@router.patch("/submission-packages/{package_id}", response_model=SubmissionPackageRead)
async def update_submission_package(
    package_id: int,
    payload: SubmissionPackageUpdate,
    user_id: int | None = Query(None, description="User ID (optional if authenticated)"),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> SubmissionPackageRead:
    """
    Update a submission package.
    """
    resolved_user_id = resolve_user_id(user_id, current_user)

    package_result = await session.execute(
        select(SubmissionPackage).where(SubmissionPackage.id == package_id)
    )
    package = package_result.scalar_one_or_none()
    if not package:
        raise HTTPException(status_code=404, detail="Submission package not found")

    proposal_result = await session.execute(
        select(Proposal).where(Proposal.id == package.proposal_id)
    )
    proposal = proposal_result.scalar_one_or_none()
    if not proposal or proposal.user_id != resolved_user_id:
        raise HTTPException(status_code=404, detail="Submission package not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(package, field, value)

    package.updated_at = datetime.utcnow()

    await log_audit_event(
        session,
        user_id=resolved_user_id,
        entity_type="submission_package",
        entity_id=package.id,
        action="proposal.submission_package.updated",
        metadata={"proposal_id": proposal.id, "package_id": package.id},
    )
    await dispatch_webhook_event(
        session,
        user_id=resolved_user_id,
        event_type="proposal.submission_package.updated",
        payload={"proposal_id": proposal.id, "package_id": package.id},
    )

    await session.commit()
    await session.refresh(package)

    return SubmissionPackageRead.model_validate(package)


@router.post("/submission-packages/{package_id}/submit", response_model=SubmissionPackageRead)
async def submit_submission_package(
    package_id: int,
    user_id: int | None = Query(None, description="User ID (optional if authenticated)"),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> SubmissionPackageRead:
    """
    Mark a submission package as submitted.
    """
    resolved_user_id = resolve_user_id(user_id, current_user)

    package_result = await session.execute(
        select(SubmissionPackage).where(SubmissionPackage.id == package_id)
    )
    package = package_result.scalar_one_or_none()
    if not package:
        raise HTTPException(status_code=404, detail="Submission package not found")

    proposal_result = await session.execute(
        select(Proposal).where(Proposal.id == package.proposal_id)
    )
    proposal = proposal_result.scalar_one_or_none()
    if not proposal or proposal.user_id != resolved_user_id:
        raise HTTPException(status_code=404, detail="Submission package not found")

    package.status = SubmissionPackageStatus.SUBMITTED
    package.submitted_at = datetime.utcnow()
    package.updated_at = datetime.utcnow()

    await log_audit_event(
        session,
        user_id=resolved_user_id,
        entity_type="submission_package",
        entity_id=package.id,
        action="proposal.submission_package.submitted",
        metadata={"proposal_id": proposal.id, "package_id": package.id},
    )
    await dispatch_webhook_event(
        session,
        user_id=resolved_user_id,
        event_type="proposal.submission_package.submitted",
        payload={"proposal_id": proposal.id, "package_id": package.id},
    )

    await session.commit()
    await session.refresh(package)

    return SubmissionPackageRead.model_validate(package)
