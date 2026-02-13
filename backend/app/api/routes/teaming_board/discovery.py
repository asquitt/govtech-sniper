"""Teaming Board - Partner Search / Discovery."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.capture import TeamingPartner
from app.schemas.teaming import TeamingPartnerPublicProfile
from app.services.auth_service import UserAuth

router = APIRouter()


@router.get("/search", response_model=list[TeamingPartnerPublicProfile])
async def search_partners(
    naics: str | None = Query(None, description="Filter by NAICS code"),
    set_aside: str | None = Query(None, description="Filter by set-aside type"),
    capability: str | None = Query(None, description="Filter by capability keyword"),
    clearance: str | None = Query(None, description="Filter by clearance level"),
    q: str | None = Query(None, description="Free-text name search"),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[TeamingPartnerPublicProfile]:
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
