"""
RFP Sniper - Capture Routes
===========================
Capture pipeline and teaming partners.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.api.deps import get_current_user
from app.services.auth_service import UserAuth
from app.models.rfp import RFP
from app.models.capture import (
    CapturePlan,
    GateReview,
    TeamingPartner,
    RFPTeamingPartner,
    CaptureCustomField,
    CaptureFieldValue,
)
from app.schemas.capture import (
    CapturePlanCreate,
    CapturePlanUpdate,
    CapturePlanRead,
    CapturePlanListItem,
    CapturePlanListResponse,
    GateReviewCreate,
    GateReviewRead,
    TeamingPartnerCreate,
    TeamingPartnerUpdate,
    TeamingPartnerRead,
    TeamingPartnerLinkCreate,
    TeamingPartnerLinkList,
    TeamingPartnerLinkRead,
    CaptureFieldCreate,
    CaptureFieldUpdate,
    CaptureFieldRead,
    CaptureFieldValueUpdate,
    CaptureFieldValueRead,
    CaptureFieldValueList,
)
from app.services.audit_service import log_audit_event
from app.services.webhook_service import dispatch_webhook_event

router = APIRouter(prefix="/capture", tags=["Capture"])


# -----------------------------------------------------------------------------
# Capture Plans
# -----------------------------------------------------------------------------

@router.post("/plans", response_model=CapturePlanRead)
async def create_capture_plan(
    payload: CapturePlanCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CapturePlanRead:
    # Ensure RFP ownership
    rfp_result = await session.execute(
        select(RFP).where(RFP.id == payload.rfp_id, RFP.user_id == current_user.id)
    )
    rfp = rfp_result.scalar_one_or_none()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    existing_result = await session.execute(
        select(CapturePlan).where(CapturePlan.rfp_id == payload.rfp_id)
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Capture plan already exists")

    plan = CapturePlan(
        rfp_id=payload.rfp_id,
        owner_id=current_user.id,
        stage=payload.stage,
        bid_decision=payload.bid_decision,
        win_probability=payload.win_probability,
        notes=payload.notes,
    )
    session.add(plan)
    await session.flush()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="capture_plan",
        entity_id=plan.id,
        action="capture.plan_created",
        metadata={"rfp_id": plan.rfp_id},
    )
    await dispatch_webhook_event(
        session,
        user_id=current_user.id,
        event_type="capture.plan_created",
        payload={"rfp_id": plan.rfp_id, "plan_id": plan.id},
    )
    await session.commit()
    await session.refresh(plan)

    return CapturePlanRead.model_validate(plan)


@router.get("/plans", response_model=CapturePlanListResponse)
async def list_capture_plans(
    include_rfp: bool = Query(False),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CapturePlanListResponse:
    result = await session.execute(
        select(CapturePlan).where(CapturePlan.owner_id == current_user.id)
    )
    plans = result.scalars().all()

    items: List[CapturePlanListItem] = []
    if include_rfp:
        rfp_result = await session.execute(
            select(RFP).where(RFP.user_id == current_user.id)
        )
        rfps = {rfp.id: rfp for rfp in rfp_result.scalars().all()}
        for plan in plans:
            rfp = rfps.get(plan.rfp_id)
            items.append(
                CapturePlanListItem(
                    **CapturePlanRead.model_validate(plan).model_dump(),
                    rfp_title=rfp.title if rfp else "Unknown",
                    rfp_agency=rfp.agency if rfp else None,
                    rfp_status=rfp.status.value if rfp else None,
                )
            )
    else:
        items = [
            CapturePlanListItem(
                **CapturePlanRead.model_validate(plan).model_dump(),
                rfp_title="",
                rfp_agency=None,
                rfp_status=None,
            )
            for plan in plans
        ]

    return CapturePlanListResponse(plans=items, total=len(items))


@router.get("/plans/{rfp_id}", response_model=CapturePlanRead)
async def get_capture_plan(
    rfp_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CapturePlanRead:
    result = await session.execute(
        select(CapturePlan)
        .where(CapturePlan.rfp_id == rfp_id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Capture plan not found")

    # Ensure ownership via RFP
    rfp_result = await session.execute(
        select(RFP).where(RFP.id == rfp_id, RFP.user_id == current_user.id)
    )
    if not rfp_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="RFP not found")

    return CapturePlanRead.model_validate(plan)


@router.patch("/plans/{plan_id}", response_model=CapturePlanRead)
async def update_capture_plan(
    plan_id: int,
    payload: CapturePlanUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CapturePlanRead:
    result = await session.execute(
        select(CapturePlan).where(CapturePlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Capture plan not found")

    # Ensure ownership via RFP
    rfp_result = await session.execute(
        select(RFP).where(RFP.id == plan.rfp_id, RFP.user_id == current_user.id)
    )
    if not rfp_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="RFP not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(plan, field, value)
    plan.updated_at = datetime.utcnow()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="capture_plan",
        entity_id=plan.id,
        action="capture.plan_updated",
        metadata={"updated_fields": list(update_data.keys())},
    )
    await dispatch_webhook_event(
        session,
        user_id=current_user.id,
        event_type="capture.plan_updated",
        payload={"plan_id": plan.id, "updated_fields": list(update_data.keys())},
    )
    await session.commit()
    await session.refresh(plan)

    return CapturePlanRead.model_validate(plan)


# -----------------------------------------------------------------------------
# Gate Reviews
# -----------------------------------------------------------------------------

@router.post("/gate-reviews", response_model=GateReviewRead)
async def create_gate_review(
    payload: GateReviewCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> GateReviewRead:
    rfp_result = await session.execute(
        select(RFP).where(RFP.id == payload.rfp_id, RFP.user_id == current_user.id)
    )
    if not rfp_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="RFP not found")

    review = GateReview(
        rfp_id=payload.rfp_id,
        reviewer_id=current_user.id,
        stage=payload.stage,
        decision=payload.decision,
        notes=payload.notes,
    )
    session.add(review)
    await session.flush()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="gate_review",
        entity_id=review.id,
        action="capture.gate_review_created",
        metadata={"rfp_id": review.rfp_id},
    )
    await dispatch_webhook_event(
        session,
        user_id=current_user.id,
        event_type="capture.gate_review_created",
        payload={"rfp_id": review.rfp_id, "review_id": review.id},
    )
    await session.commit()
    await session.refresh(review)

    return GateReviewRead.model_validate(review)


@router.get("/gate-reviews", response_model=List[GateReviewRead])
async def list_gate_reviews(
    rfp_id: int = Query(...),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[GateReviewRead]:
    rfp_result = await session.execute(
        select(RFP).where(RFP.id == rfp_id, RFP.user_id == current_user.id)
    )
    if not rfp_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="RFP not found")

    result = await session.execute(
        select(GateReview).where(GateReview.rfp_id == rfp_id)
    )
    reviews = result.scalars().all()
    return [GateReviewRead.model_validate(r) for r in reviews]


# -----------------------------------------------------------------------------
# Teaming Partners
# -----------------------------------------------------------------------------

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


@router.get("/partners", response_model=List[TeamingPartnerRead])
async def list_teaming_partners(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[TeamingPartnerRead]:
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


# -----------------------------------------------------------------------------
# Custom Fields
# -----------------------------------------------------------------------------

@router.get("/fields", response_model=List[CaptureFieldRead])
async def list_capture_fields(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[CaptureFieldRead]:
    result = await session.execute(
        select(CaptureCustomField).where(CaptureCustomField.user_id == current_user.id)
    )
    fields = result.scalars().all()
    return [CaptureFieldRead.model_validate(field) for field in fields]


@router.post("/fields", response_model=CaptureFieldRead)
async def create_capture_field(
    payload: CaptureFieldCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CaptureFieldRead:
    field = CaptureCustomField(
        user_id=current_user.id,
        name=payload.name,
        field_type=payload.field_type,
        options=payload.options or [],
        stage=payload.stage,
        is_required=payload.is_required,
    )
    session.add(field)
    await session.flush()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="capture_field",
        entity_id=field.id,
        action="capture.field_created",
        metadata={"name": field.name},
    )
    await session.commit()
    await session.refresh(field)

    return CaptureFieldRead.model_validate(field)


@router.patch("/fields/{field_id}", response_model=CaptureFieldRead)
async def update_capture_field(
    field_id: int,
    payload: CaptureFieldUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CaptureFieldRead:
    result = await session.execute(
        select(CaptureCustomField).where(
            CaptureCustomField.id == field_id,
            CaptureCustomField.user_id == current_user.id,
        )
    )
    field = result.scalar_one_or_none()
    if not field:
        raise HTTPException(status_code=404, detail="Capture field not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "options" and value is None:
            value = []
        setattr(field, key, value)
    field.updated_at = datetime.utcnow()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="capture_field",
        entity_id=field.id,
        action="capture.field_updated",
        metadata={"updated_fields": list(update_data.keys())},
    )
    await session.commit()
    await session.refresh(field)

    return CaptureFieldRead.model_validate(field)


@router.delete("/fields/{field_id}")
async def delete_capture_field(
    field_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(
        select(CaptureCustomField).where(
            CaptureCustomField.id == field_id,
            CaptureCustomField.user_id == current_user.id,
        )
    )
    field = result.scalar_one_or_none()
    if not field:
        raise HTTPException(status_code=404, detail="Capture field not found")

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="capture_field",
        entity_id=field.id,
        action="capture.field_deleted",
        metadata={"name": field.name},
    )
    await session.delete(field)
    await session.commit()

    return {"message": "Capture field deleted"}


@router.get("/plans/{plan_id}/fields", response_model=CaptureFieldValueList)
async def list_capture_plan_fields(
    plan_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CaptureFieldValueList:
    plan_result = await session.execute(
        select(CapturePlan).where(CapturePlan.id == plan_id)
    )
    plan = plan_result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Capture plan not found")

    rfp_result = await session.execute(
        select(RFP).where(RFP.id == plan.rfp_id, RFP.user_id == current_user.id)
    )
    if not rfp_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="RFP not found")

    fields_result = await session.execute(
        select(CaptureCustomField).where(CaptureCustomField.user_id == current_user.id)
    )
    fields = fields_result.scalars().all()

    values_result = await session.execute(
        select(CaptureFieldValue).where(CaptureFieldValue.capture_plan_id == plan_id)
    )
    values = {value.field_id: value for value in values_result.scalars().all()}

    payload = []
    for field in fields:
        value_entry = values.get(field.id)
        payload.append(
            CaptureFieldValueRead(
                field=CaptureFieldRead.model_validate(field),
                value=value_entry.value.get("value") if value_entry else None,
            )
        )

    return CaptureFieldValueList(fields=payload)


@router.put("/plans/{plan_id}/fields", response_model=CaptureFieldValueList)
async def update_capture_plan_fields(
    plan_id: int,
    payload: List[CaptureFieldValueUpdate],
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CaptureFieldValueList:
    plan_result = await session.execute(
        select(CapturePlan).where(CapturePlan.id == plan_id)
    )
    plan = plan_result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Capture plan not found")

    rfp_result = await session.execute(
        select(RFP).where(RFP.id == plan.rfp_id, RFP.user_id == current_user.id)
    )
    if not rfp_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="RFP not found")

    field_ids = [item.field_id for item in payload]
    if field_ids:
        fields_result = await session.execute(
            select(CaptureCustomField).where(
                CaptureCustomField.user_id == current_user.id,
                CaptureCustomField.id.in_(field_ids),
            )
        )
        fields = {field.id: field for field in fields_result.scalars().all()}
    else:
        fields = {}

    existing_values_result = await session.execute(
        select(CaptureFieldValue).where(CaptureFieldValue.capture_plan_id == plan_id)
    )
    existing_values = {value.field_id: value for value in existing_values_result.scalars().all()}

    for item in payload:
        if item.field_id not in fields:
            continue
        if item.field_id in existing_values:
            value_entry = existing_values[item.field_id]
            value_entry.value = {"value": item.value}
            value_entry.updated_at = datetime.utcnow()
        else:
            value_entry = CaptureFieldValue(
                capture_plan_id=plan_id,
                field_id=item.field_id,
                value={"value": item.value},
            )
            session.add(value_entry)

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="capture_plan",
        entity_id=plan.id,
        action="capture.fields_updated",
        metadata={"field_ids": field_ids},
    )
    await session.commit()

    return await list_capture_plan_fields(plan_id, current_user, session)
