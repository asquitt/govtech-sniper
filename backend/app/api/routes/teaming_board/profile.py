"""Teaming Board - Profile Management."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.capture import TeamingPartner
from app.schemas.teaming import TeamingPartnerExtended
from app.services.audit_service import log_audit_event
from app.services.auth_service import UserAuth

router = APIRouter()


@router.patch("/my-profile/{partner_id}", response_model=TeamingPartnerExtended)
async def update_my_partner_profile(
    partner_id: int,
    is_public: bool | None = None,
    naics_codes: list[str] | None = Query(default=None),
    set_asides: list[str] | None = Query(default=None),
    capabilities: list[str] | None = Query(default=None),
    clearance_level: str | None = None,
    past_performance_summary: str | None = None,
    website: str | None = None,
    company_duns: str | None = None,
    cage_code: str | None = None,
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
