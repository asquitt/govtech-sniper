"""
Custom Fields - Per-stage custom field definitions and values.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.capture import CaptureCustomField, CaptureFieldValue, CapturePlan
from app.models.rfp import RFP
from app.schemas.capture import (
    CaptureFieldCreate,
    CaptureFieldRead,
    CaptureFieldUpdate,
    CaptureFieldValueList,
    CaptureFieldValueRead,
    CaptureFieldValueUpdate,
)
from app.services.audit_service import log_audit_event
from app.services.auth_service import UserAuth

router = APIRouter()


@router.get("/fields", response_model=list[CaptureFieldRead])
async def list_capture_fields(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[CaptureFieldRead]:
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
    plan_result = await session.execute(select(CapturePlan).where(CapturePlan.id == plan_id))
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
    payload: list[CaptureFieldValueUpdate],
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CaptureFieldValueList:
    plan_result = await session.execute(select(CapturePlan).where(CapturePlan.id == plan_id))
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
