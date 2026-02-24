"""
Integrations Routes - SSO & Sync
==================================
SSO authorize/callback, data sync runs, and webhook event handling.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.integration import (
    IntegrationConfig,
    IntegrationProvider,
    IntegrationSyncRun,
    IntegrationSyncStatus,
    IntegrationWebhookEvent,
)
from app.services.audit_service import log_audit_event
from app.services.auth_service import UserAuth
from app.services.sso_service import exchange_sso_code

from .definitions import (
    IntegrationSsoAuthorizeResponse,
    IntegrationSsoCallbackRequest,
    IntegrationSyncResponse,
    IntegrationWebhookEventResponse,
    build_sso_authorize_url,
    get_provider_definition,
    missing_required_fields,
    prepare_config_for_internal_use,
)

router = APIRouter()


@router.post("/{integration_id}/sso/authorize", response_model=IntegrationSsoAuthorizeResponse)
async def authorize_sso(
    integration_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> IntegrationSsoAuthorizeResponse:
    result = await session.execute(
        select(IntegrationConfig).where(
            IntegrationConfig.id == integration_id,
            IntegrationConfig.user_id == current_user.id,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    definition = get_provider_definition(integration.provider)
    if definition.get("category") != "sso":
        raise HTTPException(status_code=400, detail="SSO not supported for this provider")

    missing = missing_required_fields(definition, integration.config)
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required fields: {', '.join(missing)}",
        )

    state = f"sso-{integration.id}-{int(datetime.utcnow().timestamp())}"
    config = prepare_config_for_internal_use(integration.config, definition)
    authorization_url = build_sso_authorize_url(integration.provider, config, state)

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="integration",
        entity_id=integration.id,
        action="integration.sso.authorize",
        metadata={"provider": integration.provider.value, "state": state},
    )
    await session.commit()

    return IntegrationSsoAuthorizeResponse(
        provider=integration.provider,
        authorization_url=authorization_url,
        state=state,
    )


@router.post("/{integration_id}/sso/callback")
async def sso_callback(
    integration_id: int,
    payload: IntegrationSsoCallbackRequest,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(
        select(IntegrationConfig).where(
            IntegrationConfig.id == integration_id,
            IntegrationConfig.user_id == current_user.id,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    definition = get_provider_definition(integration.provider)
    if definition.get("category") != "sso":
        raise HTTPException(status_code=400, detail="SSO not supported for this provider")

    config = prepare_config_for_internal_use(integration.config, definition)

    token_payload = None
    exchange_status = "skipped"
    if payload.code:
        try:
            token_payload = await exchange_sso_code(
                integration.provider,
                config,
                payload.code,
            )
            exchange_status = "ok"
        except Exception as exc:
            exchange_status = "error"
            token_payload = {"error": str(exc)}

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="integration",
        entity_id=integration.id,
        action="integration.sso.callback",
        metadata={
            "provider": integration.provider.value,
            "code_received": bool(payload.code),
            "exchange_status": exchange_status,
        },
    )
    await session.commit()

    return {
        "status": "ok",
        "message": "SSO callback received",
        "provider": integration.provider.value,
        "token_exchange": exchange_status,
        "token_payload": token_payload,
    }


@router.post("/{integration_id}/sync", response_model=IntegrationSyncResponse)
async def run_integration_sync(
    integration_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> IntegrationSyncResponse:
    result = await session.execute(
        select(IntegrationConfig).where(
            IntegrationConfig.id == integration_id,
            IntegrationConfig.user_id == current_user.id,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    definition = get_provider_definition(integration.provider)
    if not definition.get("supports_sync", False):
        raise HTTPException(status_code=400, detail="Sync not supported for this provider")

    missing = missing_required_fields(definition, integration.config)
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required fields: {', '.join(missing)}",
        )

    sync_run = IntegrationSyncRun(
        integration_id=integration.id,
        provider=integration.provider,
        status=IntegrationSyncStatus.RUNNING,
        items_synced=0,
        details={
            "trigger": "manual",
            "scope": integration.config.get("scope", "default"),
        },
    )
    session.add(sync_run)
    await session.flush()

    # Simulated sync work
    items_synced = 12 if integration.provider == IntegrationProvider.SHAREPOINT else 7
    sync_run.status = IntegrationSyncStatus.SUCCESS
    sync_run.items_synced = items_synced
    sync_run.completed_at = datetime.utcnow()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="integration_sync",
        entity_id=sync_run.id,
        action="integration.sync.completed",
        metadata={
            "provider": integration.provider.value,
            "items_synced": items_synced,
        },
    )
    await session.commit()
    await session.refresh(sync_run)

    return IntegrationSyncResponse.model_validate(sync_run)


@router.get("/{integration_id}/syncs", response_model=list[IntegrationSyncResponse])
async def list_integration_syncs(
    integration_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(25, ge=1, le=200),
) -> list[IntegrationSyncResponse]:
    result = await session.execute(
        select(IntegrationConfig).where(
            IntegrationConfig.id == integration_id,
            IntegrationConfig.user_id == current_user.id,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    sync_result = await session.execute(
        select(IntegrationSyncRun)
        .where(IntegrationSyncRun.integration_id == integration_id)
        .order_by(IntegrationSyncRun.started_at.desc())
        .limit(limit)
    )
    runs = sync_result.scalars().all()
    return [IntegrationSyncResponse.model_validate(run) for run in runs]


@router.post("/{integration_id}/webhook", response_model=IntegrationWebhookEventResponse)
async def receive_integration_webhook(
    integration_id: int,
    payload: dict,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> IntegrationWebhookEventResponse:
    result = await session.execute(
        select(IntegrationConfig).where(
            IntegrationConfig.id == integration_id,
            IntegrationConfig.user_id == current_user.id,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    definition = get_provider_definition(integration.provider)
    if not definition.get("supports_webhooks", False):
        raise HTTPException(status_code=400, detail="Webhooks not supported for this provider")

    event_type = payload.get("event_type") if isinstance(payload, dict) else "generic"
    event = IntegrationWebhookEvent(
        integration_id=integration.id,
        provider=integration.provider,
        event_type=event_type or "generic",
        payload=payload if isinstance(payload, dict) else {"raw": payload},
    )
    session.add(event)
    await session.flush()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="integration_webhook",
        entity_id=event.id,
        action="integration.webhook.received",
        metadata={"provider": integration.provider.value, "event_type": event.event_type},
    )
    await session.commit()
    await session.refresh(event)

    return IntegrationWebhookEventResponse.model_validate(event)


@router.get("/{integration_id}/webhooks", response_model=list[IntegrationWebhookEventResponse])
async def list_integration_webhook_events(
    integration_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(25, ge=1, le=200),
) -> list[IntegrationWebhookEventResponse]:
    result = await session.execute(
        select(IntegrationConfig).where(
            IntegrationConfig.id == integration_id,
            IntegrationConfig.user_id == current_user.id,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    events_result = await session.execute(
        select(IntegrationWebhookEvent)
        .where(IntegrationWebhookEvent.integration_id == integration_id)
        .order_by(IntegrationWebhookEvent.received_at.desc())
        .limit(limit)
    )
    events = events_result.scalars().all()
    return [IntegrationWebhookEventResponse.model_validate(event) for event in events]
