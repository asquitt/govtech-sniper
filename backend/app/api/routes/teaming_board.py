"""
RFP Sniper - Teaming Board Routes
==================================
Partner discovery and teaming requests.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.api.deps import get_current_user
from app.services.auth_service import UserAuth
from app.models.capture import TeamingPartner, TeamingRequest, TeamingRequestStatus
from app.schemas.teaming import (
    TeamingPartnerExtended,
    TeamingPartnerPublicProfile,
    TeamingRequestCreate,
    TeamingRequestRead,
    TeamingRequestUpdate,
)
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/teaming", tags=["Teaming Board"])


# -----------------------------------------------------------------------------
# Partner Search / Discovery
# -----------------------------------------------------------------------------


@router.get("/search", response_model=List[TeamingPartnerPublicProfile])
async def search_partners(
    naics: Optional[str] = Query(None, description="Filter by NAICS code"),
    set_aside: Optional[str] = Query(None, description="Filter by set-aside type"),
    capability: Optional[str] = Query(None, description="Filter by capability keyword"),
    clearance: Optional[str] = Query(None, description="Filter by clearance level"),
    q: Optional[str] = Query(None, description="Free-text name search"),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[TeamingPartnerPublicProfile]:
    """Search public partner profiles with optional filters."""
    stmt = select(TeamingPartner).where(TeamingPartner.is_public == True)  # noqa: E712

    if q:
        stmt = stmt.where(TeamingPartner.name.ilike(f"%{q}%"))

    results = await session.execute(stmt)
    partners = results.scalars().all()

    # Apply JSON-field filters in Python (SQLite/Postgres JSON compatibility)
    filtered = []
    for p in partners:
        if naics and naics not in (p.naics_codes or []):
            continue
        if set_aside and set_aside not in (p.set_asides or []):
            continue
        if capability:
            caps = [c.lower() for c in (p.capabilities or [])]
            if not any(capability.lower() in c for c in caps):
                continue
        if clearance and (p.clearance_level or "").lower() != clearance.lower():
            continue
        filtered.append(p)

    return [TeamingPartnerPublicProfile.model_validate(p) for p in filtered]


@router.get("/profile/{partner_id}", response_model=TeamingPartnerPublicProfile)
async def get_partner_profile(
    partner_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TeamingPartnerPublicProfile:
    """Get a public partner profile by ID."""
    result = await session.execute(
        select(TeamingPartner).where(
            TeamingPartner.id == partner_id,
            TeamingPartner.is_public == True,  # noqa: E712
        )
    )
    partner = result.scalar_one_or_none()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found or not public")

    return TeamingPartnerPublicProfile.model_validate(partner)


# -----------------------------------------------------------------------------
# My Profile (make own partner record public/private)
# -----------------------------------------------------------------------------


@router.patch("/my-profile/{partner_id}", response_model=TeamingPartnerExtended)
async def update_my_partner_profile(
    partner_id: int,
    is_public: Optional[bool] = None,
    naics_codes: Optional[List[str]] = None,
    set_asides: Optional[List[str]] = None,
    capabilities: Optional[List[str]] = None,
    clearance_level: Optional[str] = None,
    past_performance_summary: Optional[str] = None,
    website: Optional[str] = None,
    company_duns: Optional[str] = None,
    cage_code: Optional[str] = None,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TeamingPartnerExtended:
    """Update extended fields on your own partner profile."""
    result = await session.execute(
        select(TeamingPartner).where(
            TeamingPartner.id == partner_id,
            TeamingPartner.user_id == current_user.id,
        )
    )
    partner = result.scalar_one_or_none()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    if is_public is not None:
        partner.is_public = is_public
    if naics_codes is not None:
        partner.naics_codes = naics_codes
    if set_asides is not None:
        partner.set_asides = set_asides
    if capabilities is not None:
        partner.capabilities = capabilities
    if clearance_level is not None:
        partner.clearance_level = clearance_level
    if past_performance_summary is not None:
        partner.past_performance_summary = past_performance_summary
    if website is not None:
        partner.website = website
    if company_duns is not None:
        partner.company_duns = company_duns
    if cage_code is not None:
        partner.cage_code = cage_code

    partner.updated_at = datetime.utcnow()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="teaming_partner",
        entity_id=partner.id,
        action="teaming.profile_updated",
        metadata={"is_public": partner.is_public},
    )
    await session.commit()
    await session.refresh(partner)

    return TeamingPartnerExtended.model_validate(partner)


# -----------------------------------------------------------------------------
# Teaming Requests
# -----------------------------------------------------------------------------


@router.post("/requests", response_model=TeamingRequestRead)
async def send_teaming_request(
    payload: TeamingRequestCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TeamingRequestRead:
    """Send a teaming request to a public partner."""
    # Verify partner exists and is public
    partner_result = await session.execute(
        select(TeamingPartner).where(
            TeamingPartner.id == payload.to_partner_id,
            TeamingPartner.is_public == True,  # noqa: E712
        )
    )
    partner = partner_result.scalar_one_or_none()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found or not public")

    # Check for duplicate pending request
    existing = await session.execute(
        select(TeamingRequest).where(
            TeamingRequest.from_user_id == current_user.id,
            TeamingRequest.to_partner_id == payload.to_partner_id,
            TeamingRequest.status == TeamingRequestStatus.PENDING,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Pending request already exists")

    request = TeamingRequest(
        from_user_id=current_user.id,
        to_partner_id=payload.to_partner_id,
        rfp_id=payload.rfp_id,
        message=payload.message,
    )
    session.add(request)
    await session.flush()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="teaming_request",
        entity_id=request.id,
        action="teaming.request_sent",
        metadata={"to_partner_id": payload.to_partner_id},
    )
    await session.commit()
    await session.refresh(request)

    return TeamingRequestRead(
        id=request.id,
        from_user_id=request.from_user_id,
        to_partner_id=request.to_partner_id,
        rfp_id=request.rfp_id,
        message=request.message,
        status=request.status.value,
        partner_name=partner.name,
        created_at=request.created_at,
        updated_at=request.updated_at,
    )


@router.get("/requests", response_model=List[TeamingRequestRead])
async def list_teaming_requests(
    direction: str = Query("sent", description="'sent' or 'received'"),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[TeamingRequestRead]:
    """List sent or received teaming requests."""
    if direction == "received":
        # Requests to partners owned by current user
        my_partner_result = await session.execute(
            select(TeamingPartner.id).where(
                TeamingPartner.user_id == current_user.id
            )
        )
        my_partner_ids = [pid for pid in my_partner_result.scalars().all()]

        if not my_partner_ids:
            return []

        result = await session.execute(
            select(TeamingRequest).where(
                TeamingRequest.to_partner_id.in_(my_partner_ids)
            )
        )
    else:
        result = await session.execute(
            select(TeamingRequest).where(
                TeamingRequest.from_user_id == current_user.id
            )
        )

    requests = result.scalars().all()

    # Fetch partner names
    partner_ids = list({r.to_partner_id for r in requests})
    if partner_ids:
        partners_result = await session.execute(
            select(TeamingPartner).where(TeamingPartner.id.in_(partner_ids))
        )
        partner_map = {p.id: p.name for p in partners_result.scalars().all()}
    else:
        partner_map = {}

    return [
        TeamingRequestRead(
            id=r.id,
            from_user_id=r.from_user_id,
            to_partner_id=r.to_partner_id,
            rfp_id=r.rfp_id,
            message=r.message,
            status=r.status.value if isinstance(r.status, TeamingRequestStatus) else r.status,
            partner_name=partner_map.get(r.to_partner_id),
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in requests
    ]


@router.patch("/requests/{request_id}", response_model=TeamingRequestRead)
async def update_teaming_request(
    request_id: int,
    payload: TeamingRequestUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TeamingRequestRead:
    """Accept or decline a teaming request (must own the target partner)."""
    if payload.status not in ("accepted", "declined"):
        raise HTTPException(status_code=400, detail="Status must be 'accepted' or 'declined'")

    result = await session.execute(
        select(TeamingRequest).where(TeamingRequest.id == request_id)
    )
    request = result.scalar_one_or_none()
    if not request:
        raise HTTPException(status_code=404, detail="Teaming request not found")

    # Verify current user owns the target partner
    partner_result = await session.execute(
        select(TeamingPartner).where(
            TeamingPartner.id == request.to_partner_id,
            TeamingPartner.user_id == current_user.id,
        )
    )
    partner = partner_result.scalar_one_or_none()
    if not partner:
        raise HTTPException(status_code=403, detail="Not authorized to update this request")

    request.status = TeamingRequestStatus(payload.status)
    request.updated_at = datetime.utcnow()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="teaming_request",
        entity_id=request.id,
        action=f"teaming.request_{payload.status}",
        metadata={"from_user_id": request.from_user_id},
    )
    await session.commit()
    await session.refresh(request)

    return TeamingRequestRead(
        id=request.id,
        from_user_id=request.from_user_id,
        to_partner_id=request.to_partner_id,
        rfp_id=request.rfp_id,
        message=request.message,
        status=request.status.value if isinstance(request.status, TeamingRequestStatus) else request.status,
        partner_name=partner.name,
        created_at=request.created_at,
        updated_at=request.updated_at,
    )
