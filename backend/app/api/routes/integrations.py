"""
RFP Sniper - Integrations Routes
================================
CRUD for integration configurations.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.api.deps import get_current_user
from app.services.auth_service import UserAuth
from app.models.integration import (
    IntegrationConfig,
    IntegrationProvider,
    IntegrationSyncRun,
    IntegrationSyncStatus,
    IntegrationWebhookEvent,
)
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/integrations", tags=["Integrations"])


PROVIDER_DEFINITIONS: Dict[IntegrationProvider, Dict[str, Any]] = {
    IntegrationProvider.OKTA: {
        "label": "Okta",
        "category": "sso",
        "required_fields": [
            {"key": "domain", "label": "Okta Domain", "secret": False},
            {"key": "client_id", "label": "Client ID", "secret": False},
            {"key": "client_secret", "label": "Client Secret", "secret": True},
            {"key": "issuer", "label": "Issuer URL", "secret": False},
            {"key": "redirect_uri", "label": "Redirect URI", "secret": False},
        ],
        "optional_fields": [
            {"key": "scopes", "label": "Scopes", "secret": False},
            {"key": "group_claim", "label": "Group Claim", "secret": False},
        ],
        "supports_sync": False,
        "supports_webhooks": False,
    },
    IntegrationProvider.MICROSOFT: {
        "label": "Microsoft Entra ID",
        "category": "sso",
        "required_fields": [
            {"key": "tenant_id", "label": "Tenant ID", "secret": False},
            {"key": "client_id", "label": "Client ID", "secret": False},
            {"key": "client_secret", "label": "Client Secret", "secret": True},
            {"key": "redirect_uri", "label": "Redirect URI", "secret": False},
        ],
        "optional_fields": [
            {"key": "authority", "label": "Authority URL", "secret": False},
            {"key": "scopes", "label": "Scopes", "secret": False},
        ],
        "supports_sync": False,
        "supports_webhooks": False,
    },
    IntegrationProvider.SHAREPOINT: {
        "label": "SharePoint",
        "category": "content",
        "required_fields": [
            {"key": "site_url", "label": "Site URL", "secret": False},
            {"key": "tenant_id", "label": "Tenant ID", "secret": False},
            {"key": "client_id", "label": "Client ID", "secret": False},
            {"key": "client_secret", "label": "Client Secret", "secret": True},
        ],
        "optional_fields": [
            {"key": "drive_id", "label": "Drive ID", "secret": False},
            {"key": "library_name", "label": "Library Name", "secret": False},
        ],
        "supports_sync": True,
        "supports_webhooks": True,
    },
    IntegrationProvider.SALESFORCE: {
        "label": "Salesforce",
        "category": "crm",
        "required_fields": [
            {"key": "instance_url", "label": "Instance URL", "secret": False},
            {"key": "client_id", "label": "Client ID", "secret": False},
            {"key": "client_secret", "label": "Client Secret", "secret": True},
            {"key": "username", "label": "Username", "secret": False},
            {"key": "security_token", "label": "Security Token", "secret": True},
        ],
        "optional_fields": [
            {"key": "sandbox", "label": "Sandbox", "secret": False},
            {"key": "api_version", "label": "API Version", "secret": False},
        ],
        "supports_sync": True,
        "supports_webhooks": True,
    },
    IntegrationProvider.WORD_ADDIN: {
        "label": "Word Add-in",
        "category": "productivity",
        "required_fields": [
            {"key": "tenant_id", "label": "Tenant ID", "secret": False},
            {"key": "app_id", "label": "Add-in App ID", "secret": False},
        ],
        "optional_fields": [],
        "supports_sync": False,
        "supports_webhooks": False,
    },
    IntegrationProvider.WEBHOOK: {
        "label": "Webhook",
        "category": "automation",
        "required_fields": [
            {"key": "target_url", "label": "Target URL", "secret": False},
        ],
        "optional_fields": [
            {"key": "secret", "label": "Signing Secret", "secret": True},
        ],
        "supports_sync": False,
        "supports_webhooks": False,
    },
    IntegrationProvider.SLACK: {
        "label": "Slack",
        "category": "notifications",
        "required_fields": [
            {"key": "webhook_url", "label": "Webhook URL", "secret": False},
        ],
        "optional_fields": [
            {"key": "channel", "label": "Channel", "secret": False},
        ],
        "supports_sync": False,
        "supports_webhooks": False,
    },
}


class IntegrationCreate(BaseModel):
    provider: IntegrationProvider
    name: Optional[str] = None
    is_enabled: bool = True
    config: dict = Field(default_factory=dict)


class IntegrationUpdate(BaseModel):
    name: Optional[str] = None
    is_enabled: Optional[bool] = None
    config: Optional[dict] = None


class IntegrationProviderDefinition(BaseModel):
    provider: IntegrationProvider
    label: str
    category: str
    required_fields: List[dict]
    optional_fields: List[dict]
    supports_sync: bool
    supports_webhooks: bool


class IntegrationTestResult(BaseModel):
    status: str
    message: str
    missing_fields: List[str]
    checked_at: datetime


class IntegrationSyncResponse(BaseModel):
    id: int
    status: IntegrationSyncStatus
    items_synced: int
    error: Optional[str]
    details: dict
    started_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class IntegrationWebhookEventResponse(BaseModel):
    id: int
    event_type: str
    payload: dict
    received_at: datetime

    model_config = {"from_attributes": True}


class IntegrationSsoAuthorizeResponse(BaseModel):
    provider: IntegrationProvider
    authorization_url: str
    state: str


class IntegrationSsoCallbackRequest(BaseModel):
    code: str


def _get_provider_definition(provider: IntegrationProvider) -> Dict[str, Any]:
    definition = PROVIDER_DEFINITIONS.get(provider)
    if not definition:
        raise HTTPException(status_code=400, detail="Unsupported provider")
    return definition


def _missing_required_fields(definition: Dict[str, Any], config: dict) -> List[str]:
    config = config or {}
    missing = []
    for field in definition.get("required_fields", []):
        key = field.get("key")
        if not key:
            continue
        value = config.get(key)
        if value is None or value == "":
            missing.append(key)
    return missing


def _build_sso_authorize_url(provider: IntegrationProvider, config: dict, state: str) -> str:
    config = config or {}
    client_id = config.get("client_id", "")
    redirect_uri = config.get("redirect_uri", "")
    scopes = config.get("scopes", "openid profile email")

    if provider == IntegrationProvider.OKTA:
        domain = config.get("domain", "")
        base = f"https://{domain}/oauth2/default/v1/authorize"
        return (
            f"{base}?client_id={client_id}&response_type=code&scope={scopes}"
            f"&redirect_uri={redirect_uri}&state={state}"
        )

    if provider == IntegrationProvider.MICROSOFT:
        tenant_id = config.get("tenant_id", "")
        base = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
        return (
            f"{base}?client_id={client_id}&response_type=code&scope={scopes}"
            f"&redirect_uri={redirect_uri}&state={state}"
        )

    raise HTTPException(status_code=400, detail="SSO not supported for this provider")


class IntegrationResponse(BaseModel):
    id: int
    provider: IntegrationProvider
    name: Optional[str]
    is_enabled: bool
    config: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


@router.get("/providers", response_model=List[IntegrationProviderDefinition])
async def list_integration_providers(
    current_user: UserAuth = Depends(get_current_user),
) -> List[IntegrationProviderDefinition]:
    """
    List supported integration providers and their configuration requirements.
    """
    _ = current_user
    definitions = []
    for provider, definition in PROVIDER_DEFINITIONS.items():
        definitions.append(
            IntegrationProviderDefinition(
                provider=provider,
                label=definition["label"],
                category=definition["category"],
                required_fields=definition["required_fields"],
                optional_fields=definition["optional_fields"],
                supports_sync=definition["supports_sync"],
                supports_webhooks=definition["supports_webhooks"],
            )
        )
    return definitions


@router.get("", response_model=List[IntegrationResponse])
async def list_integrations(
    provider: Optional[IntegrationProvider] = Query(None),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[IntegrationResponse]:
    query = select(IntegrationConfig).where(IntegrationConfig.user_id == current_user.id)
    if provider:
        query = query.where(IntegrationConfig.provider == provider)

    result = await session.execute(query)
    integrations = result.scalars().all()
    return [IntegrationResponse.model_validate(i) for i in integrations]


@router.post("", response_model=IntegrationResponse)
async def create_integration(
    payload: IntegrationCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> IntegrationResponse:
    integration = IntegrationConfig(
        user_id=current_user.id,
        provider=payload.provider,
        name=payload.name,
        is_enabled=payload.is_enabled,
        config=payload.config or {},
    )
    session.add(integration)
    await session.flush()
    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="integration",
        entity_id=integration.id,
        action="integration.created",
        metadata={"provider": integration.provider.value, "name": integration.name},
    )
    await session.commit()
    await session.refresh(integration)

    return IntegrationResponse.model_validate(integration)


@router.patch("/{integration_id}", response_model=IntegrationResponse)
async def update_integration(
    integration_id: int,
    payload: IntegrationUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> IntegrationResponse:
    result = await session.execute(
        select(IntegrationConfig).where(
            IntegrationConfig.id == integration_id,
            IntegrationConfig.user_id == current_user.id,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(integration, field, value)
    integration.updated_at = datetime.utcnow()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="integration",
        entity_id=integration.id,
        action="integration.updated",
        metadata={"updated_fields": list(update_data.keys())},
    )
    await session.commit()
    await session.refresh(integration)

    return IntegrationResponse.model_validate(integration)


@router.post("/{integration_id}/test", response_model=IntegrationTestResult)
async def test_integration(
    integration_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> IntegrationTestResult:
    result = await session.execute(
        select(IntegrationConfig).where(
            IntegrationConfig.id == integration_id,
            IntegrationConfig.user_id == current_user.id,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    definition = _get_provider_definition(integration.provider)
    missing_fields = _missing_required_fields(definition, integration.config)

    if not integration.is_enabled:
        status = "disabled"
        message = "Integration is disabled."
    elif missing_fields:
        status = "error"
        message = "Missing required configuration fields."
    else:
        status = "ok"
        message = "Integration configuration looks valid."

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="integration",
        entity_id=integration.id,
        action="integration.tested",
        metadata={"status": status, "missing_fields": missing_fields},
    )
    await session.commit()

    return IntegrationTestResult(
        status=status,
        message=message,
        missing_fields=missing_fields,
        checked_at=datetime.utcnow(),
    )


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

    definition = _get_provider_definition(integration.provider)
    if definition.get("category") != "sso":
        raise HTTPException(status_code=400, detail="SSO not supported for this provider")

    missing_fields = _missing_required_fields(definition, integration.config)
    if missing_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required fields: {', '.join(missing_fields)}",
        )

    state = f"sso-{integration.id}-{int(datetime.utcnow().timestamp())}"
    authorization_url = _build_sso_authorize_url(
        integration.provider, integration.config, state
    )

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

    definition = _get_provider_definition(integration.provider)
    if definition.get("category") != "sso":
        raise HTTPException(status_code=400, detail="SSO not supported for this provider")

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="integration",
        entity_id=integration.id,
        action="integration.sso.callback",
        metadata={
            "provider": integration.provider.value,
            "code_received": bool(payload.code),
        },
    )
    await session.commit()

    return {"status": "ok", "message": "SSO callback received"}


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

    definition = _get_provider_definition(integration.provider)
    if not definition.get("supports_sync", False):
        raise HTTPException(status_code=400, detail="Sync not supported for this provider")

    missing_fields = _missing_required_fields(definition, integration.config)
    if missing_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required fields: {', '.join(missing_fields)}",
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


@router.get("/{integration_id}/syncs", response_model=List[IntegrationSyncResponse])
async def list_integration_syncs(
    integration_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(25, ge=1, le=200),
) -> List[IntegrationSyncResponse]:
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

    definition = _get_provider_definition(integration.provider)
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


@router.get("/{integration_id}/webhooks", response_model=List[IntegrationWebhookEventResponse])
async def list_integration_webhook_events(
    integration_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(25, ge=1, le=200),
) -> List[IntegrationWebhookEventResponse]:
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


@router.delete("/{integration_id}")
async def delete_integration(
    integration_id: int,
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

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="integration",
        entity_id=integration.id,
        action="integration.deleted",
        metadata={"provider": integration.provider.value, "name": integration.name},
    )
    await session.delete(integration)
    await session.commit()

    return {"message": "Integration deleted"}
