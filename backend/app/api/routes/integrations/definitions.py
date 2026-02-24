"""
Integrations Routes - Definitions & Helpers
=============================================
Provider definitions, Pydantic schemas, and shared utility functions.
"""

from datetime import datetime
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field

from app.models.integration import (
    IntegrationProvider,
    IntegrationSyncStatus,
)
from app.services.encryption_service import (
    decrypt_secrets,
    encrypt_secrets,
    redact_secrets,
    secret_placeholder,
)

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


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------


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


class IntegrationResponse(BaseModel):
    id: int
    provider: IntegrationProvider
    name: str | None
    is_enabled: bool
    config: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def get_provider_definition(provider: IntegrationProvider) -> dict[str, Any]:
    definition = PROVIDER_DEFINITIONS.get(provider)
    if not definition:
        raise HTTPException(status_code=400, detail="Unsupported provider")
    return definition


def missing_required_fields(definition: dict[str, Any], config: dict) -> list[str]:
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


def secret_field_keys(definition: dict[str, Any]) -> list[str]:
    fields = definition.get("required_fields", []) + definition.get("optional_fields", [])
    return [field["key"] for field in fields if field.get("secret")]


def merge_integration_config(
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


def prepare_config_for_storage(config: dict, definition: dict[str, Any]) -> dict:
    fields = secret_field_keys(definition)
    return encrypt_secrets(config or {}, fields)


def prepare_config_for_response(config: dict, definition: dict[str, Any]) -> dict:
    fields = secret_field_keys(definition)
    return redact_secrets(config or {}, fields)


def prepare_config_for_internal_use(config: dict, definition: dict[str, Any]) -> dict:
    fields = secret_field_keys(definition)
    return decrypt_secrets(config or {}, fields)


def build_sso_authorize_url(provider: IntegrationProvider, config: dict, state: str) -> str:
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
