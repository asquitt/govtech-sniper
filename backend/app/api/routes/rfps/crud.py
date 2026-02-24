"""
RFP Routes - CRUD Operations
=============================
List, create, update, delete RFPs and summary statistics.
"""

from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import (
    get_current_user,
    get_current_user_optional,
    resolve_user_id,
)
from app.database import get_session
from app.models.rfp import RFP, RFPStatus
from app.schemas.rfp import (
    RFPCreate,
    RFPListItem,
    RFPRead,
    RFPUpdate,
)
from app.services.audit_service import log_audit_event
from app.services.auth_service import UserAuth
from app.services.cache_service import cache_clear_prefix, cache_get, cache_set
from app.services.embedding_service import (
    compose_rfp_text,
    delete_entity_embeddings,
    index_entity,
)
from app.services.webhook_service import dispatch_webhook_event

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("/", response_model=list[RFPListItem])
async def list_rfps(
    user_id: int | None = Query(None, description="User ID (optional if authenticated)"),
    status: RFPStatus | None = Query(None, description="Filter by status"),
    qualified_only: bool = Query(False, description="Only show qualified RFPs"),
    source_type: str | None = Query(None, description="Filter by source type"),
    jurisdiction: str | None = Query(None, description="Filter by jurisdiction"),
    currency: str | None = Query(None, description="Filter by currency code"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> list[RFPListItem]:
    """
    List RFPs for a user with optional filtering.
    """
    resolved_user_id = resolve_user_id(user_id, current_user)
    cache_key = (
        f"rfps:list:{resolved_user_id}:{status}:{qualified_only}:{source_type}:"
        f"{jurisdiction}:{currency}:{skip}:{limit}"
    )
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    query = select(RFP).where(RFP.user_id == resolved_user_id)

    if status:
        query = query.where(RFP.status == status)

    if qualified_only:
        query = query.where(RFP.is_qualified == True)

    if source_type:
        source_values = [item.strip() for item in source_type.split(",") if item.strip()]
        if len(source_values) == 1:
            query = query.where(RFP.source_type == source_values[0])
        elif source_values:
            query = query.where(RFP.source_type.in_(source_values))

    if jurisdiction:
        jurisdiction_values = [item.strip() for item in jurisdiction.split(",") if item.strip()]
        if len(jurisdiction_values) == 1:
            query = query.where(RFP.jurisdiction == jurisdiction_values[0])
        elif jurisdiction_values:
            query = query.where(RFP.jurisdiction.in_(jurisdiction_values))

    if currency:
        currency_values = [item.strip().upper() for item in currency.split(",") if item.strip()]
        if len(currency_values) == 1:
            query = query.where(RFP.currency == currency_values[0])
        elif currency_values:
            query = query.where(RFP.currency.in_(currency_values))

    query = query.order_by(RFP.created_at.desc()).offset(skip).limit(limit)

    result = await session.execute(query)
    rfps = result.scalars().all()
    payload = [RFPListItem.model_validate(rfp).model_dump() for rfp in rfps]
    await cache_set(cache_key, payload)
    return payload


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


@router.get("/{rfp_id}", response_model=RFPRead)
async def get_rfp(
    rfp_id: int = Path(..., description="RFP ID"),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> RFPRead:
    """
    Get detailed RFP information.
    """
    result = await session.execute(select(RFP).where(RFP.id == rfp_id))
    rfp = result.scalar_one_or_none()

    if not rfp or rfp.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"RFP {rfp_id} not found")

    return RFPRead.model_validate(rfp)


@router.post("/", response_model=RFPRead)
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
    try:
        await index_entity(
            session,
            user_id=resolved_user_id,
            entity_type="rfp",
            entity_id=rfp.id,
            text=compose_rfp_text(
                title=rfp.title,
                solicitation_number=rfp.solicitation_number,
                agency=rfp.agency,
                sub_agency=rfp.sub_agency,
                naics_code=rfp.naics_code,
                set_aside=rfp.set_aside,
                description=rfp.description,
                full_text=rfp.full_text,
                summary=rfp.summary,
            ),
        )
    except Exception as exc:
        logger.warning("RFP semantic index update failed", rfp_id=rfp.id, error=str(exc))
    await session.commit()
    await session.refresh(rfp)
    await cache_clear_prefix(f"rfps:list:{resolved_user_id}:")

    return RFPRead.model_validate(rfp)


@router.patch("/{rfp_id}", response_model=RFPRead)
async def update_rfp(
    rfp_id: int,
    update_data: RFPUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> RFPRead:
    """
    Update RFP fields.
    """
    result = await session.execute(select(RFP).where(RFP.id == rfp_id))
    rfp = result.scalar_one_or_none()

    if not rfp or rfp.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"RFP {rfp_id} not found")

    # Apply updates
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(rfp, field, value)

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
    try:
        await index_entity(
            session,
            user_id=rfp.user_id,
            entity_type="rfp",
            entity_id=rfp.id,
            text=compose_rfp_text(
                title=rfp.title,
                solicitation_number=rfp.solicitation_number,
                agency=rfp.agency,
                sub_agency=rfp.sub_agency,
                naics_code=rfp.naics_code,
                set_aside=rfp.set_aside,
                description=rfp.description,
                full_text=rfp.full_text,
                summary=rfp.summary,
            ),
        )
    except Exception as exc:
        logger.warning("RFP semantic reindex failed", rfp_id=rfp.id, error=str(exc))
    await session.commit()
    await session.refresh(rfp)
    await cache_clear_prefix(f"rfps:list:{rfp.user_id}:")

    return RFPRead.model_validate(rfp)


@router.delete("/{rfp_id}")
async def delete_rfp(
    rfp_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Delete an RFP and all related data.
    """
    result = await session.execute(select(RFP).where(RFP.id == rfp_id))
    rfp = result.scalar_one_or_none()

    if not rfp or rfp.user_id != current_user.id:
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
    try:
        await delete_entity_embeddings(
            session,
            user_id=rfp.user_id,
            entity_type="rfp",
            entity_id=rfp.id,
        )
    except Exception as exc:
        logger.warning("RFP embedding cleanup failed", rfp_id=rfp.id, error=str(exc))
    await session.delete(rfp)
    await session.commit()
    await cache_clear_prefix(f"rfps:list:{rfp.user_id}:")

    return {"message": f"RFP {rfp_id} deleted"}


@router.post("/{rfp_id}/upload-pdf")
async def upload_rfp_pdf(
    rfp_id: int,
    current_user: UserAuth = Depends(get_current_user),
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
