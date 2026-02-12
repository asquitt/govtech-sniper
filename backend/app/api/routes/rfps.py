"""
RFP Sniper - RFP Management Routes
===================================
CRUD operations for RFPs.
"""

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user_optional, resolve_user_id
from app.database import get_session
from app.models.opportunity_snapshot import SAMOpportunitySnapshot
from app.models.rfp import RFP, RFPStatus
from app.schemas.rfp import (
    RFPCreate,
    RFPListItem,
    RFPRead,
    RFPUpdate,
    SAMOpportunitySnapshotDiff,
    SAMOpportunitySnapshotRead,
)
from app.services.audit_service import log_audit_event
from app.services.auth_service import UserAuth
from app.services.cache_service import cache_clear_prefix, cache_get, cache_set
from app.services.snapshot_service import build_snapshot_summary, diff_snapshot_summaries
from app.services.webhook_service import dispatch_webhook_event

router = APIRouter(prefix="/rfps", tags=["RFPs"])


@router.get("", response_model=list[RFPListItem])
async def list_rfps(
    user_id: int | None = Query(None, description="User ID (optional if authenticated)"),
    status: RFPStatus | None = Query(None, description="Filter by status"),
    qualified_only: bool = Query(False, description="Only show qualified RFPs"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> list[RFPListItem]:
    """
    List RFPs for a user with optional filtering.
    """
    resolved_user_id = resolve_user_id(user_id, current_user)
    cache_key = f"rfps:list:{resolved_user_id}:{status}:{qualified_only}:{skip}:{limit}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    query = select(RFP).where(RFP.user_id == resolved_user_id)

    if status:
        query = query.where(RFP.status == status)

    if qualified_only:
        query = query.where(RFP.is_qualified == True)

    query = query.order_by(RFP.created_at.desc()).offset(skip).limit(limit)

    result = await session.execute(query)
    rfps = result.scalars().all()
    payload = [RFPListItem.model_validate(rfp).model_dump() for rfp in rfps]
    await cache_set(cache_key, payload)
    return payload


@router.get("/{rfp_id}", response_model=RFPRead)
async def get_rfp(
    rfp_id: int = Path(..., description="RFP ID"),
    session: AsyncSession = Depends(get_session),
) -> RFPRead:
    """
    Get detailed RFP information.
    """
    result = await session.execute(select(RFP).where(RFP.id == rfp_id))
    rfp = result.scalar_one_or_none()

    if not rfp:
        raise HTTPException(status_code=404, detail=f"RFP {rfp_id} not found")

    return RFPRead.model_validate(rfp)


@router.get("/{rfp_id}/snapshots", response_model=list[SAMOpportunitySnapshotRead])
async def list_rfp_snapshots(
    rfp_id: int = Path(..., description="RFP ID"),
    include_raw: bool = Query(False, description="Include raw SAM.gov payload"),
    limit: int = Query(20, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> list[SAMOpportunitySnapshotRead]:
    """
    List SAM.gov opportunity snapshots for an RFP.
    """
    rfp_result = await session.execute(select(RFP).where(RFP.id == rfp_id))
    rfp = rfp_result.scalar_one_or_none()
    if not rfp:
        raise HTTPException(status_code=404, detail=f"RFP {rfp_id} not found")

    result = await session.execute(
        select(SAMOpportunitySnapshot)
        .where(SAMOpportunitySnapshot.rfp_id == rfp_id)
        .order_by(desc(SAMOpportunitySnapshot.fetched_at))
        .limit(limit)
    )
    snapshots = result.scalars().all()

    response = []
    for snapshot in snapshots:
        summary = build_snapshot_summary(snapshot.raw_payload)
        response.append(
            SAMOpportunitySnapshotRead(
                id=snapshot.id,
                notice_id=snapshot.notice_id,
                solicitation_number=snapshot.solicitation_number,
                rfp_id=snapshot.rfp_id,
                user_id=snapshot.user_id,
                fetched_at=snapshot.fetched_at,
                posted_date=snapshot.posted_date,
                response_deadline=snapshot.response_deadline,
                raw_hash=snapshot.raw_hash,
                summary=summary,
                raw_payload=snapshot.raw_payload if include_raw else None,
            )
        )

    return response


@router.get("/{rfp_id}/snapshots/diff", response_model=SAMOpportunitySnapshotDiff)
async def diff_rfp_snapshots(
    rfp_id: int = Path(..., description="RFP ID"),
    from_snapshot_id: int | None = Query(
        None, description="Snapshot ID to diff from (defaults to previous)"
    ),
    to_snapshot_id: int | None = Query(
        None, description="Snapshot ID to diff to (defaults to latest)"
    ),
    session: AsyncSession = Depends(get_session),
) -> SAMOpportunitySnapshotDiff:
    """
    Diff two snapshots for an RFP.
    """
    rfp_result = await session.execute(select(RFP).where(RFP.id == rfp_id))
    rfp = rfp_result.scalar_one_or_none()
    if not rfp:
        raise HTTPException(status_code=404, detail=f"RFP {rfp_id} not found")

    if from_snapshot_id and to_snapshot_id:
        snapshots_result = await session.execute(
            select(SAMOpportunitySnapshot).where(
                SAMOpportunitySnapshot.id.in_([from_snapshot_id, to_snapshot_id]),
                SAMOpportunitySnapshot.rfp_id == rfp_id,
            )
        )
        snapshots = {s.id: s for s in snapshots_result.scalars().all()}
        from_snapshot = snapshots.get(from_snapshot_id)
        to_snapshot = snapshots.get(to_snapshot_id)
    else:
        snapshots_result = await session.execute(
            select(SAMOpportunitySnapshot)
            .where(SAMOpportunitySnapshot.rfp_id == rfp_id)
            .order_by(desc(SAMOpportunitySnapshot.fetched_at))
            .limit(2)
        )
        snapshots = snapshots_result.scalars().all()
        if len(snapshots) < 2:
            raise HTTPException(
                status_code=404,
                detail="Not enough snapshots to diff",
            )
        to_snapshot = snapshots[0]
        from_snapshot = snapshots[1]

    if not from_snapshot or not to_snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found for this RFP")

    summary_from = build_snapshot_summary(from_snapshot.raw_payload)
    summary_to = build_snapshot_summary(to_snapshot.raw_payload)
    changes = diff_snapshot_summaries(summary_from, summary_to)

    return SAMOpportunitySnapshotDiff(
        from_snapshot_id=from_snapshot.id,
        to_snapshot_id=to_snapshot.id,
        changes=changes,
        summary_from=summary_from,
        summary_to=summary_to,
    )


@router.post("", response_model=RFPRead)
async def create_rfp(
    rfp_data: RFPCreate,
    user_id: int | None = Query(None, description="User ID (optional if authenticated)"),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> RFPRead:
    """
    Manually create an RFP record.

    Use this for RFPs not found via SAM.gov or imported from other sources.
    """
    resolved_user_id = resolve_user_id(user_id, current_user)

    # Check for duplicate solicitation number within the same user scope.
    existing = await session.execute(
        select(RFP).where(
            RFP.user_id == resolved_user_id,
            RFP.solicitation_number == rfp_data.solicitation_number,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"RFP with solicitation number {rfp_data.solicitation_number} already exists",
        )

    rfp = RFP(
        user_id=resolved_user_id,
        **rfp_data.model_dump(),
    )
    session.add(rfp)
    await session.flush()
    await log_audit_event(
        session,
        user_id=resolved_user_id,
        entity_type="rfp",
        entity_id=rfp.id,
        action="rfp.created",
        metadata={"title": rfp.title, "solicitation_number": rfp.solicitation_number},
    )
    await dispatch_webhook_event(
        session,
        user_id=resolved_user_id,
        event_type="rfp.created",
        payload={
            "rfp_id": rfp.id,
            "title": rfp.title,
            "solicitation_number": rfp.solicitation_number,
            "agency": rfp.agency,
            "status": rfp.status,
        },
    )
    await session.commit()
    await session.refresh(rfp)
    await cache_clear_prefix(f"rfps:list:{resolved_user_id}:")

    return RFPRead.model_validate(rfp)


@router.patch("/{rfp_id}", response_model=RFPRead)
async def update_rfp(
    rfp_id: int,
    update_data: RFPUpdate,
    session: AsyncSession = Depends(get_session),
) -> RFPRead:
    """
    Update RFP fields.
    """
    result = await session.execute(select(RFP).where(RFP.id == rfp_id))
    rfp = result.scalar_one_or_none()

    if not rfp:
        raise HTTPException(status_code=404, detail=f"RFP {rfp_id} not found")

    # Apply updates
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(rfp, field, value)

    from datetime import datetime

    rfp.updated_at = datetime.utcnow()

    await log_audit_event(
        session,
        user_id=rfp.user_id,
        entity_type="rfp",
        entity_id=rfp.id,
        action="rfp.updated",
        metadata={"updated_fields": list(update_dict.keys())},
    )
    await dispatch_webhook_event(
        session,
        user_id=rfp.user_id,
        event_type="rfp.updated",
        payload={
            "rfp_id": rfp.id,
            "updated_fields": list(update_dict.keys()),
        },
    )
    await session.commit()
    await session.refresh(rfp)
    await cache_clear_prefix(f"rfps:list:{rfp.user_id}:")

    return RFPRead.model_validate(rfp)


@router.delete("/{rfp_id}")
async def delete_rfp(
    rfp_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Delete an RFP and all related data.
    """
    result = await session.execute(select(RFP).where(RFP.id == rfp_id))
    rfp = result.scalar_one_or_none()

    if not rfp:
        raise HTTPException(status_code=404, detail=f"RFP {rfp_id} not found")

    await log_audit_event(
        session,
        user_id=rfp.user_id,
        entity_type="rfp",
        entity_id=rfp.id,
        action="rfp.deleted",
        metadata={"title": rfp.title, "solicitation_number": rfp.solicitation_number},
    )
    await dispatch_webhook_event(
        session,
        user_id=rfp.user_id,
        event_type="rfp.deleted",
        payload={
            "rfp_id": rfp.id,
            "title": rfp.title,
            "solicitation_number": rfp.solicitation_number,
        },
    )
    await session.delete(rfp)
    await session.commit()
    await cache_clear_prefix(f"rfps:list:{rfp.user_id}:")

    return {"message": f"RFP {rfp_id} deleted"}


@router.post("/{rfp_id}/match-score")
async def compute_match_score(
    rfp_id: int = Path(..., description="RFP ID"),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Compute AI match score for an RFP against the user's profile."""
    from app.models.user import UserProfile
    from app.services.matching_service import OpportunityMatchingService

    result = await session.execute(select(RFP).where(RFP.id == rfp_id))
    rfp = result.scalar_one_or_none()
    if not rfp:
        raise HTTPException(status_code=404, detail=f"RFP {rfp_id} not found")

    profile_result = await session.execute(
        select(UserProfile).where(UserProfile.user_id == rfp.user_id)
    )
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=400, detail="User profile not found. Create a profile first."
        )

    service = OpportunityMatchingService()
    match = await service.score_opportunity(rfp, profile)

    rfp.match_score = match.overall_score
    rfp.match_reasoning = match.reasoning
    rfp.match_details = match.to_dict()

    from datetime import datetime

    rfp.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(rfp)

    return {
        "rfp_id": rfp.id,
        "match_score": match.overall_score,
        "category_scores": match.category_scores,
        "strengths": match.strengths,
        "gaps": match.gaps,
        "reasoning": match.reasoning,
    }


@router.post("/{rfp_id}/upload-pdf")
async def upload_rfp_pdf(
    rfp_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Upload a PDF for an RFP.

    **TODO:** Implement file upload handling.
    This endpoint will:
    1. Accept a PDF file upload
    2. Extract text using pdfplumber
    3. Store the text in rfp.full_text
    4. Trigger analysis
    """
    # Placeholder for file upload implementation
    raise HTTPException(
        status_code=501,
        detail="PDF upload not yet implemented",
    )


@router.get("/stats/summary")
async def get_rfp_stats(
    user_id: int | None = Query(None, description="User ID (optional if authenticated)"),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Get summary statistics for a user's RFPs.
    """
    from sqlalchemy import func

    resolved_user_id = resolve_user_id(user_id, current_user)

    # Total count
    total_result = await session.execute(
        select(func.count(RFP.id)).where(RFP.user_id == resolved_user_id)
    )
    total = total_result.scalar()

    # By status
    status_result = await session.execute(
        select(RFP.status, func.count(RFP.id))
        .where(RFP.user_id == resolved_user_id)
        .group_by(RFP.status)
    )
    by_status = {status.value: count for status, count in status_result.all()}

    # Qualified vs not
    qualified_result = await session.execute(
        select(func.count(RFP.id)).where(RFP.user_id == resolved_user_id, RFP.is_qualified == True)
    )
    qualified = qualified_result.scalar()

    disqualified_result = await session.execute(
        select(func.count(RFP.id)).where(RFP.user_id == resolved_user_id, RFP.is_qualified == False)
    )
    disqualified = disqualified_result.scalar()

    return {
        "total": total,
        "by_status": by_status,
        "qualified": qualified,
        "disqualified": disqualified,
        "pending_filter": total - (qualified or 0) - (disqualified or 0),
    }
