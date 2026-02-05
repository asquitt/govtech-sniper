"""
RFP Sniper - Webhooks Routes
============================
Manage webhook subscriptions.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.api.deps import get_current_user
from app.services.auth_service import UserAuth
from app.models.webhook import WebhookSubscription, WebhookDelivery
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


class WebhookCreate(BaseModel):
    name: str
    target_url: HttpUrl
    secret: Optional[str] = None
    event_types: List[str] = []
    is_active: bool = True


class WebhookUpdate(BaseModel):
    name: Optional[str] = None
    target_url: Optional[HttpUrl] = None
    secret: Optional[str] = None
    event_types: Optional[List[str]] = None
    is_active: Optional[bool] = None


class WebhookResponse(BaseModel):
    id: int
    name: str
    target_url: str
    secret: Optional[str]
    event_types: List[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DeliveryResponse(BaseModel):
    id: int
    subscription_id: int
    event_type: str
    payload: dict
    status: str
    response_code: Optional[int]
    response_body: Optional[str]
    created_at: datetime
    delivered_at: Optional[datetime]

    model_config = {"from_attributes": True}


@router.get("", response_model=List[WebhookResponse])
async def list_webhooks(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[WebhookResponse]:
    result = await session.execute(
        select(WebhookSubscription).where(WebhookSubscription.user_id == current_user.id)
    )
    webhooks = result.scalars().all()
    return [WebhookResponse.model_validate(w) for w in webhooks]


@router.post("", response_model=WebhookResponse)
async def create_webhook(
    payload: WebhookCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WebhookResponse:
    webhook = WebhookSubscription(
        user_id=current_user.id,
        name=payload.name,
        target_url=str(payload.target_url),
        secret=payload.secret,
        event_types=payload.event_types or [],
        is_active=payload.is_active,
    )
    session.add(webhook)
    await session.flush()
    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="webhook",
        entity_id=webhook.id,
        action="webhook.created",
        metadata={"name": webhook.name, "target_url": webhook.target_url},
    )
    await session.commit()
    await session.refresh(webhook)

    return WebhookResponse.model_validate(webhook)


@router.patch("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: int,
    payload: WebhookUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WebhookResponse:
    result = await session.execute(
        select(WebhookSubscription).where(
            WebhookSubscription.id == webhook_id,
            WebhookSubscription.user_id == current_user.id,
        )
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(webhook, field, value)
    webhook.updated_at = datetime.utcnow()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="webhook",
        entity_id=webhook.id,
        action="webhook.updated",
        metadata={"updated_fields": list(update_data.keys())},
    )
    await session.commit()
    await session.refresh(webhook)

    return WebhookResponse.model_validate(webhook)


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(
        select(WebhookSubscription).where(
            WebhookSubscription.id == webhook_id,
            WebhookSubscription.user_id == current_user.id,
        )
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="webhook",
        entity_id=webhook.id,
        action="webhook.deleted",
        metadata={"name": webhook.name, "target_url": webhook.target_url},
    )
    await session.delete(webhook)
    await session.commit()

    return {"message": "Webhook deleted"}


@router.get("/{webhook_id}/deliveries", response_model=List[DeliveryResponse])
async def list_webhook_deliveries(
    webhook_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[DeliveryResponse]:
    # Ensure ownership
    result = await session.execute(
        select(WebhookSubscription).where(
            WebhookSubscription.id == webhook_id,
            WebhookSubscription.user_id == current_user.id,
        )
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    deliveries_result = await session.execute(
        select(WebhookDelivery).where(WebhookDelivery.subscription_id == webhook_id)
    )
    deliveries = deliveries_result.scalars().all()
    return [DeliveryResponse.model_validate(d) for d in deliveries]
