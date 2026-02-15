"""
Admin routes - Organization CRUD + capability health.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import (
    UserAuth,
    get_current_user,
    get_org_security_policy_from_settings,
    merge_org_security_policy_settings,
)
from app.config import settings
from app.database import get_session
from app.models.integration import IntegrationConfig
from app.models.organization import (
    Organization,
    OrganizationMember,
    OrgRole,
)
from app.models.secret import SecretRecord
from app.models.user import User
from app.models.webhook import WebhookSubscription

from .helpers import (
    _celery_broker_available,
    _celery_worker_available,
    _database_engine_name,
    _require_org_admin,
    _websocket_runtime_snapshot,
)
from .schemas import OrgCreate, OrgUpdate

router = APIRouter()


@router.post("/organizations")
async def create_organization(
    body: OrgCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Create a new organization. The creator becomes the owner."""
    # Check slug uniqueness
    existing = (
        await session.execute(select(Organization).where(Organization.slug == body.slug))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Organization slug already taken")

    org = Organization(
        name=body.name,
        slug=body.slug,
        domain=body.domain,
        billing_email=body.billing_email,
    )
    session.add(org)
    await session.flush()

    # Add creator as owner
    member = OrganizationMember(
        organization_id=org.id,  # type: ignore[arg-type]
        user_id=current_user.id,
        role=OrgRole.OWNER,
    )
    session.add(member)

    # Link user to org
    user = (
        await session.execute(select(User).where(User.id == current_user.id))
    ).scalar_one_or_none()
    if user:
        user.organization_id = org.id
        session.add(user)

    await session.commit()
    await session.refresh(org)

    return {
        "id": org.id,
        "name": org.name,
        "slug": org.slug,
        "domain": org.domain,
        "created_at": org.created_at.isoformat(),
    }


@router.get("/organization")
async def get_organization(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get current user's organization details."""
    org, _member = await _require_org_admin(current_user, session)
    member_count = (
        await session.execute(
            select(func.count()).where(
                OrganizationMember.organization_id == org.id,
                OrganizationMember.is_active == True,  # noqa: E712
            )
        )
    ).scalar_one() or 0
    security_policy = get_org_security_policy_from_settings(org.settings)

    return {
        "id": org.id,
        "name": org.name,
        "slug": org.slug,
        "domain": org.domain,
        "billing_email": org.billing_email,
        "sso_enabled": org.sso_enabled,
        "sso_provider": org.sso_provider,
        "sso_enforce": org.sso_enforce,
        "sso_auto_provision": org.sso_auto_provision,
        "logo_url": org.logo_url,
        "primary_color": org.primary_color,
        "ip_allowlist": org.ip_allowlist,
        "data_retention_days": org.data_retention_days,
        "require_step_up_for_sensitive_exports": security_policy[
            "require_step_up_for_sensitive_exports"
        ],
        "require_step_up_for_sensitive_shares": security_policy[
            "require_step_up_for_sensitive_shares"
        ],
        "apply_cui_watermark_to_sensitive_exports": security_policy[
            "apply_cui_watermark_to_sensitive_exports"
        ],
        "apply_cui_redaction_to_sensitive_exports": security_policy[
            "apply_cui_redaction_to_sensitive_exports"
        ],
        "member_count": member_count,
        "created_at": org.created_at.isoformat(),
    }


@router.patch("/organization")
async def update_organization(
    body: OrgUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Update organization settings. Requires admin/owner."""
    org, _ = await _require_org_admin(current_user, session)

    update_data = body.model_dump(exclude_unset=True)
    security_updates = {
        key: update_data.pop(key)
        for key in (
            "require_step_up_for_sensitive_exports",
            "require_step_up_for_sensitive_shares",
            "apply_cui_watermark_to_sensitive_exports",
            "apply_cui_redaction_to_sensitive_exports",
        )
        if key in update_data
    }
    for field, value in update_data.items():
        setattr(org, field, value)
    if security_updates:
        org.settings = merge_org_security_policy_settings(org.settings, security_updates)
    org.updated_at = datetime.utcnow()
    session.add(org)
    await session.commit()

    return {"status": "updated"}


@router.get("/capability-health")
async def get_capability_health(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Summarized capability integration and operational health for admins."""
    org, _ = await _require_org_admin(current_user, session)

    integrations = (
        await session.execute(
            select(IntegrationConfig).where(IntegrationConfig.user_id == current_user.id)
        )
    ).scalars()
    integration_by_provider: dict[str, dict[str, int]] = {}
    for integration in integrations:
        provider = (
            integration.provider.value
            if hasattr(integration.provider, "value")
            else str(integration.provider)
        )
        bucket = integration_by_provider.setdefault(provider, {"total": 0, "enabled": 0})
        bucket["total"] += 1
        if integration.is_enabled:
            bucket["enabled"] += 1

    secret_count = (
        await session.execute(select(func.count()).where(SecretRecord.user_id == current_user.id))
    ).scalar_one() or 0
    webhook_count = (
        await session.execute(
            select(func.count()).where(WebhookSubscription.user_id == current_user.id)
        )
    ).scalar_one() or 0

    broker_reachable = _celery_broker_available()
    worker_online = _celery_worker_available()
    task_mode = "queued" if broker_reachable and worker_online else "sync_fallback"
    scim_configured = bool(settings.scim_bearer_token)
    websocket_runtime = _websocket_runtime_snapshot()

    discoverability = [
        {
            "capability": "Template Marketplace",
            "frontend_path": "/templates",
            "backend_prefix": "/api/v1/templates",
            "status": "integrated",
            "note": "Primary dashboard navigation route enabled.",
        },
        {
            "capability": "Word Add-in",
            "frontend_path": "/word-addin",
            "backend_prefix": "/api/v1/word-addin",
            "status": "integrated",
            "note": "Primary dashboard navigation route enabled with taskpane redirect.",
        },
        {
            "capability": "SCIM Provisioning",
            "frontend_path": None,
            "backend_prefix": "/api/v1/scim/v2",
            "status": "configured" if scim_configured else "needs_configuration",
            "note": (
                "SCIM bearer token configured."
                if scim_configured
                else "Set SCIM_BEARER_TOKEN to enable SCIM provisioning."
            ),
        },
        {
            "capability": "Webhook Subscriptions",
            "frontend_path": "/settings",
            "backend_prefix": "/api/v1/webhooks",
            "status": "configured" if webhook_count > 0 else "ready",
            "note": (
                f"{webhook_count} webhook subscriptions configured for current user."
                if webhook_count > 0
                else "No webhook subscriptions configured yet."
            ),
        },
        {
            "capability": "Secrets Vault",
            "frontend_path": "/settings",
            "backend_prefix": "/api/v1/secrets",
            "status": "configured" if secret_count > 0 else "ready",
            "note": (
                f"{secret_count} secrets stored for current user."
                if secret_count > 0
                else "No secrets stored yet."
            ),
        },
        {
            "capability": "WebSocket Task Feed",
            "frontend_path": "/diagnostics",
            "backend_prefix": "/api/v1/ws",
            "status": "integrated",
            "note": (
                f"{websocket_runtime['active_connections']} active socket connections, "
                f"{websocket_runtime['watched_tasks']} watched tasks, "
                f"{websocket_runtime['active_section_locks']} section locks."
            ),
        },
    ]

    return {
        "organization_id": org.id,
        "timestamp": datetime.utcnow().isoformat(),
        "runtime": {
            "debug": settings.debug,
            "mock_ai": settings.mock_ai,
            "mock_sam_gov": settings.mock_sam_gov,
            "database_engine": _database_engine_name(settings.database_url),
            "websocket": {
                "endpoint": "/api/v1/ws?token=<jwt>",
                "active_connections": websocket_runtime["active_connections"],
                "watched_tasks": websocket_runtime["watched_tasks"],
                "active_documents": websocket_runtime["active_documents"],
                "presence_users": websocket_runtime["presence_users"],
                "active_section_locks": websocket_runtime["active_section_locks"],
                "active_cursors": websocket_runtime["active_cursors"],
            },
        },
        "workers": {
            "broker_reachable": broker_reachable,
            "worker_online": worker_online,
            "task_mode": task_mode,
        },
        "enterprise": {
            "scim_configured": scim_configured,
            "scim_default_team_name": settings.scim_default_team_name,
            "webhook_subscriptions": webhook_count,
            "stored_secrets": secret_count,
        },
        "integrations_by_provider": [
            {"provider": provider, **counts}
            for provider, counts in sorted(integration_by_provider.items(), key=lambda p: p[0])
        ],
        "discoverability": discoverability,
    }
