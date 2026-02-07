"""
RFP Sniper - Alert Service
==========================
Helper to compute operational alert counts.
"""

from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.audit import AuditEvent
from app.models.integration import IntegrationConfig, IntegrationSyncRun, IntegrationSyncStatus
from app.models.webhook import WebhookDelivery, WebhookDeliveryStatus, WebhookSubscription


async def get_alert_counts(
    session: AsyncSession,
    *,
    user_id: int | None,
    days: int,
) -> dict:
    start_date = datetime.utcnow() - timedelta(days=days)

    sync_failed_query = (
        select(func.count(IntegrationSyncRun.id))
        .join(IntegrationConfig, IntegrationConfig.id == IntegrationSyncRun.integration_id)
        .where(IntegrationSyncRun.status == IntegrationSyncStatus.FAILED)
        .where(IntegrationSyncRun.started_at >= start_date)
    )
    if user_id is not None:
        sync_failed_query = sync_failed_query.where(IntegrationConfig.user_id == user_id)

    sync_failed_result = await session.execute(sync_failed_query)
    sync_failed_count = sync_failed_result.scalar() or 0

    webhook_failed_query = (
        select(func.count(WebhookDelivery.id))
        .join(WebhookSubscription, WebhookSubscription.id == WebhookDelivery.subscription_id)
        .where(WebhookDelivery.status == WebhookDeliveryStatus.FAILED)
        .where(WebhookDelivery.created_at >= start_date)
    )
    if user_id is not None:
        webhook_failed_query = webhook_failed_query.where(WebhookSubscription.user_id == user_id)

    webhook_failed_result = await session.execute(webhook_failed_query)
    webhook_failed_count = webhook_failed_result.scalar() or 0

    auth_failed_query = select(func.count(AuditEvent.id)).where(
        AuditEvent.action == "user.login_failed",
        AuditEvent.created_at >= start_date,
    )
    if user_id is not None:
        auth_failed_query = auth_failed_query.where(AuditEvent.user_id == user_id)

    auth_failed_result = await session.execute(auth_failed_query)
    auth_failed_count = auth_failed_result.scalar() or 0

    return {
        "sync_failures": sync_failed_count,
        "webhook_failures": webhook_failed_count,
        "auth_failures": auth_failed_count,
    }
