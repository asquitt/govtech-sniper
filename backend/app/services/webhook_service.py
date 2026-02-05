"""
RFP Sniper - Webhook Service
============================
Dispatch webhook events and store delivery logs.
"""

from datetime import datetime
from typing import Optional, List

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.config import settings
from app.models.webhook import (
    WebhookSubscription,
    WebhookDelivery,
    WebhookDeliveryStatus,
)


async def dispatch_webhook_event(
    session: AsyncSession,
    *,
    user_id: int,
    event_type: str,
    payload: dict,
) -> List[WebhookDelivery]:
    """
    Dispatch a webhook event to all matching subscriptions.
    Always records a delivery entry.
    """
    result = await session.execute(
        select(WebhookSubscription).where(
            WebhookSubscription.user_id == user_id,
            WebhookSubscription.is_active == True,
        )
    )
    subscriptions = result.scalars().all()
    deliveries: List[WebhookDelivery] = []

    for subscription in subscriptions:
        if subscription.event_types and event_type not in subscription.event_types:
            continue

        delivery = WebhookDelivery(
            subscription_id=subscription.id,
            event_type=event_type,
            payload=payload,
            status=WebhookDeliveryStatus.PENDING,
        )
        session.add(delivery)
        await session.flush()

        if not settings.webhook_delivery_enabled:
            delivery.status = WebhookDeliveryStatus.SKIPPED
            delivery.delivered_at = datetime.utcnow()
            deliveries.append(delivery)
            continue

        try:
            headers = {
                "Content-Type": "application/json",
                "X-Webhook-Event": event_type,
            }
            if subscription.secret:
                headers["X-Webhook-Secret"] = subscription.secret

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(subscription.target_url, json=payload, headers=headers)

            delivery.response_code = response.status_code
            delivery.response_body = response.text
            delivery.delivered_at = datetime.utcnow()

            if 200 <= response.status_code < 300:
                delivery.status = WebhookDeliveryStatus.DELIVERED
            else:
                delivery.status = WebhookDeliveryStatus.FAILED
        except Exception as exc:
            delivery.status = WebhookDeliveryStatus.FAILED
            delivery.response_body = str(exc)
            delivery.delivered_at = datetime.utcnow()

        deliveries.append(delivery)

    return deliveries
