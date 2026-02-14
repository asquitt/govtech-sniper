"""
RFP Sniper - Integrations Routes
================================
CRUD for integration configurations.
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
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
from app.services.encryption_service import (
    decrypt_secrets,
    encrypt_secrets,
    redact_secrets,
    secret_placeholder,
)
from app.services.sso_service import exchange_sso_code

router = APIRouter(prefix="/integrations", tags=["Integrations"])


PROVIDER_DEFINITIONS: dict[IntegrationProvider, dict[str, Any]] = {
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
    IntegrationProvider.UNANET: {
        "label": "Unanet",
        "category": "erp",
        "required_fields": [
            {"key": "base_url", "label": "Base URL", "secret": False},
        ],
        "optional_fields": [
            {"key": "auth_type", "label": "Auth Type (bearer/api_key/basic)", "secret": False},
            {"key": "access_token", "label": "Access Token", "secret": True},
            {"key": "api_key", "label": "API Key", "secret": True},
            {"key": "api_key_header", "label": "API Key Header", "secret": False},
            {"key": "username", "label": "Username", "secret": False},
            {"key": "password", "label": "Password", "secret": True},
            {"key": "projects_endpoint", "label": "Projects Endpoint", "secret": False},
            {"key": "resources_endpoint", "label": "Resources Endpoint", "secret": False},
            {"key": "financials_endpoint", "label": "Financials Endpoint", "secret": False},
            {"key": "sync_endpoint", "label": "Project Sync Endpoint", "secret": False},
            {"key": "resource_sync_endpoint", "label": "Resource Sync Endpoint", "secret": False},
            {
                "key": "financial_sync_endpoint",
                "label": "Financial Sync Endpoint",
                "secret": False,
            },
        ],
        "supports_sync": True,
        "supports_webhooks": False,
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
    name: str | None = None
    is_enabled: bool = True
    config: dict = Field(default_factory=dict)


class IntegrationUpdate(BaseModel):
    name: str | None = None
    is_enabled: bool | None = None
    config: dict | None = None


class IntegrationProviderDefinition(BaseModel):
    provider: IntegrationProvider
    label: str
    category: str
    required_fields: list[dict]
    optional_fields: list[dict]
    supports_sync: bool
    supports_webhooks: bool


class IntegrationTestResult(BaseModel):
    status: str
    message: str
    missing_fields: list[str]
    checked_at: datetime


class IntegrationSyncResponse(BaseModel):
    id: int
    status: IntegrationSyncStatus
    items_synced: int
    error: str | None
    details: dict
    started_at: datetime
    completed_at: datetime | None

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


def _get_provider_definition(provider: IntegrationProvider) -> dict[str, Any]:
    definition = PROVIDER_DEFINITIONS.get(provider)
    if not definition:
        raise HTTPException(status_code=400, detail="Unsupported provider")
    return definition


def _missing_required_fields(definition: dict[str, Any], config: dict) -> list[str]:
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


def _secret_field_keys(definition: dict[str, Any]) -> list[str]:
    fields = definition.get("required_fields", []) + definition.get("optional_fields", [])
    return [field["key"] for field in fields if field.get("secret")]


def _merge_integration_config(
    existing: dict,
    incoming: dict | None,
    secret_fields: list[str],
) -> dict:
    if not incoming:
        return existing
    merged = dict(existing or {})
    for key, value in (incoming or {}).items():
        if key in secret_fields and value == secret_placeholder():
            continue
        merged[key] = value
    return merged


def _prepare_config_for_storage(config: dict, definition: dict[str, Any]) -> dict:
    secret_fields = _secret_field_keys(definition)
    return encrypt_secrets(config or {}, secret_fields)


def _prepare_config_for_response(config: dict, definition: dict[str, Any]) -> dict:
    secret_fields = _secret_field_keys(definition)
    return redact_secrets(config or {}, secret_fields)


def _prepare_config_for_internal_use(config: dict, definition: dict[str, Any]) -> dict:
    secret_fields = _secret_field_keys(definition)
    return decrypt_secrets(config or {}, secret_fields)


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
    name: str | None
    is_enabled: bool
    config: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


@router.get("/providers", response_model=list[IntegrationProviderDefinition])
async def list_integration_providers(
    current_user: UserAuth = Depends(get_current_user),
) -> list[IntegrationProviderDefinition]:
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


@router.get("", response_model=list[IntegrationResponse])
async def list_integrations(
    provider: IntegrationProvider | None = Query(None),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[IntegrationResponse]:
    query = select(IntegrationConfig).where(IntegrationConfig.user_id == current_user.id)
    if provider:
        query = query.where(IntegrationConfig.provider == provider)

    result = await session.execute(query)
    integrations = result.scalars().all()
    response = []
    for integration in integrations:
        definition = _get_provider_definition(integration.provider)
        response.append(
            IntegrationResponse(
                id=integration.id,
                provider=integration.provider,
                name=integration.name,
                is_enabled=integration.is_enabled,
                config=_prepare_config_for_response(integration.config, definition),
                created_at=integration.created_at,
                updated_at=integration.updated_at,
            )
        )
    return response


@router.post("", response_model=IntegrationResponse)
async def create_integration(
    payload: IntegrationCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> IntegrationResponse:
    definition = _get_provider_definition(payload.provider)
    config = _prepare_config_for_storage(payload.config or {}, definition)
    integration = IntegrationConfig(
        user_id=current_user.id,
        provider=payload.provider,
        name=payload.name,
        is_enabled=payload.is_enabled,
        config=config,
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

    return IntegrationResponse(
        id=integration.id,
        provider=integration.provider,
        name=integration.name,
        is_enabled=integration.is_enabled,
        config=_prepare_config_for_response(integration.config, definition),
        created_at=integration.created_at,
        updated_at=integration.updated_at,
    )


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

    definition = _get_provider_definition(integration.provider)
    secret_fields = _secret_field_keys(definition)
    update_data = payload.model_dump(exclude_unset=True)
    if "config" in update_data:
        merged = _merge_integration_config(
            integration.config,
            update_data.get("config"),
            secret_fields,
        )
        update_data["config"] = _prepare_config_for_storage(merged, definition)
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

    return IntegrationResponse(
        id=integration.id,
        provider=integration.provider,
        name=integration.name,
        is_enabled=integration.is_enabled,
        config=_prepare_config_for_response(integration.config, definition),
        created_at=integration.created_at,
        updated_at=integration.updated_at,
    )


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
    config = _prepare_config_for_internal_use(integration.config, definition)
    authorization_url = _build_sso_authorize_url(integration.provider, config, state)

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

    config = _prepare_config_for_internal_use(integration.config, definition)

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
