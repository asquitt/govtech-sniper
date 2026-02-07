"""
Teaming Partners - Partner CRUD and RFP linking.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.capture import RFPTeamingPartner, TeamingPartner
from app.models.rfp import RFP
from app.schemas.capture import (
    TeamingPartnerCreate,
    TeamingPartnerLinkCreate,
    TeamingPartnerLinkList,
    TeamingPartnerLinkRead,
    TeamingPartnerRead,
    TeamingPartnerUpdate,
)
from app.services.audit_service import log_audit_event
from app.services.auth_service import UserAuth
from app.services.webhook_service import dispatch_webhook_event

router = APIRouter()


@router.post("/partners", response_model=TeamingPartnerRead)
async def create_teaming_partner(
    payload: TeamingPartnerCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TeamingPartnerRead:
    partner = TeamingPartner(
        user_id=current_user.id,
        name=payload.name,
        partner_type=payload.partner_type,
        contact_name=payload.contact_name,
        contact_email=payload.contact_email,
        notes=payload.notes,
    )
    session.add(partner)
    await session.flush()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="teaming_partner",
        entity_id=partner.id,
        action="capture.partner_created",
        metadata={"name": partner.name},
    )
    await session.commit()
    await session.refresh(partner)

    return TeamingPartnerRead.model_validate(partner)


@router.get("/partners", response_model=list[TeamingPartnerRead])
async def list_teaming_partners(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[TeamingPartnerRead]:
    result = await session.execute(
        select(TeamingPartner).where(TeamingPartner.user_id == current_user.id)
    )
    partners = result.scalars().all()
    return [TeamingPartnerRead.model_validate(p) for p in partners]


@router.patch("/partners/{partner_id}", response_model=TeamingPartnerRead)
async def update_teaming_partner(
    partner_id: int,
    payload: TeamingPartnerUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TeamingPartnerRead:
    result = await session.execute(
        select(TeamingPartner).where(
            TeamingPartner.id == partner_id,
            TeamingPartner.user_id == current_user.id,
        )
    )
    partner = result.scalar_one_or_none()
    if not partner:
        raise HTTPException(status_code=404, detail="Teaming partner not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(partner, field, value)
    partner.updated_at = datetime.utcnow()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="teaming_partner",
        entity_id=partner.id,
        action="capture.partner_updated",
        metadata={"updated_fields": list(update_data.keys())},
    )
    await session.commit()
    await session.refresh(partner)

    return TeamingPartnerRead.model_validate(partner)


@router.delete("/partners/{partner_id}")
async def delete_teaming_partner(
    partner_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(
        select(TeamingPartner).where(
            TeamingPartner.id == partner_id,
            TeamingPartner.user_id == current_user.id,
        )
    )
    partner = result.scalar_one_or_none()
    if not partner:
        raise HTTPException(status_code=404, detail="Teaming partner not found")

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="teaming_partner",
        entity_id=partner.id,
        action="capture.partner_deleted",
        metadata={"name": partner.name},
    )
    await session.delete(partner)
    await session.commit()

    return {"message": "Teaming partner deleted"}


@router.post("/partners/link", response_model=TeamingPartnerLinkRead)
async def link_teaming_partner(
    payload: TeamingPartnerLinkCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TeamingPartnerLinkRead:
    # Ensure RFP ownership
    rfp_result = await session.execute(
        select(RFP).where(RFP.id == payload.rfp_id, RFP.user_id == current_user.id)
    )
    if not rfp_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="RFP not found")

    partner_result = await session.execute(
        select(TeamingPartner).where(
            TeamingPartner.id == payload.partner_id,
            TeamingPartner.user_id == current_user.id,
        )
    )
    partner = partner_result.scalar_one_or_none()
    if not partner:
        raise HTTPException(status_code=404, detail="Teaming partner not found")

    link = RFPTeamingPartner(
        rfp_id=payload.rfp_id,
        partner_id=payload.partner_id,
        role=payload.role,
    )
    session.add(link)
    await session.flush()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="rfp_teaming_partner",
        entity_id=link.id,
        action="capture.partner_linked",
        metadata={"rfp_id": link.rfp_id, "partner_id": link.partner_id},
    )
    await dispatch_webhook_event(
        session,
        user_id=current_user.id,
        event_type="capture.partner_linked",
        payload={"rfp_id": link.rfp_id, "partner_id": link.partner_id},
    )
    await session.commit()
    await session.refresh(link)

    return TeamingPartnerLinkRead.model_validate(link)


@router.get("/partners/links", response_model=TeamingPartnerLinkList)
async def list_teaming_partner_links(
    rfp_id: int = Query(...),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TeamingPartnerLinkList:
    rfp_result = await session.execute(
        select(RFP).where(RFP.id == rfp_id, RFP.user_id == current_user.id)
    )
    if not rfp_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="RFP not found")

    result = await session.execute(
        select(RFPTeamingPartner).where(RFPTeamingPartner.rfp_id == rfp_id)
    )
    links = result.scalars().all()
    data = [TeamingPartnerLinkRead.model_validate(l) for l in links]
    return TeamingPartnerLinkList(links=data, total=len(data))
