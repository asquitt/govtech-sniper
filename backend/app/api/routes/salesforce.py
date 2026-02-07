"""
RFP Sniper - Salesforce Integration Routes
=============================================
Salesforce CRM sync, field mappings, and webhook ingestion.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.integration import IntegrationConfig, IntegrationProvider
from app.models.salesforce_mapping import SalesforceFieldMapping
from app.schemas.salesforce import (
    SalesforceFieldMappingCreate,
    SalesforceFieldMappingRead,
    SalesforceOpportunityRead,
    SalesforceSyncResult,
)
from app.services.auth_service import UserAuth
from app.services.encryption_service import decrypt_secrets
from app.services.salesforce_service import create_salesforce_service

router = APIRouter(prefix="/salesforce", tags=["Salesforce"])

SF_SECRET_FIELDS = ["client_secret", "security_token"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_sf_integration(user_id: int, session: AsyncSession) -> IntegrationConfig:
    """Load the user's enabled Salesforce integration."""
    result = await session.execute(
        select(IntegrationConfig).where(
            IntegrationConfig.user_id == user_id,
            IntegrationConfig.provider == IntegrationProvider.SALESFORCE,
            IntegrationConfig.is_enabled == True,  # noqa: E712
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(404, "Salesforce integration not configured or disabled")
    return config


async def _build_sf_service(integration: IntegrationConfig):
    """Decrypt secrets and build the SalesforceService."""
    decrypted = decrypt_secrets(integration.config or {}, SF_SECRET_FIELDS)
    try:
        return create_salesforce_service(decrypted)
    except ValueError as e:
        raise HTTPException(400, str(e))


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/status")
async def salesforce_status(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Check if Salesforce integration is configured and connected."""
    result = await session.execute(
        select(IntegrationConfig).where(
            IntegrationConfig.user_id == current_user.id,
            IntegrationConfig.provider == IntegrationProvider.SALESFORCE,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        return {"configured": False, "enabled": False, "connected": False}

    if not config.is_enabled:
        return {"configured": True, "enabled": False, "connected": False}

    try:
        svc = await _build_sf_service(config)
        await svc._get_token()
        return {"configured": True, "enabled": True, "connected": True}
    except Exception as e:
        return {
            "configured": True,
            "enabled": True,
            "connected": False,
            "error": str(e),
        }


@router.get("/opportunities", response_model=list[SalesforceOpportunityRead])
async def list_opportunities(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[SalesforceOpportunityRead]:
    """List Salesforce opportunities."""
    integration = await _get_sf_integration(current_user.id, session)
    svc = await _build_sf_service(integration)
    try:
        opps = await svc.pull_opportunities()
        return [SalesforceOpportunityRead(**o) for o in opps]
    except Exception as e:
        raise HTTPException(502, f"Salesforce API error: {e}")


@router.post("/sync", response_model=SalesforceSyncResult)
async def trigger_sync(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SalesforceSyncResult:
    """Trigger a bidirectional sync between Sniper and Salesforce."""
    integration = await _get_sf_integration(current_user.id, session)
    svc = await _build_sf_service(integration)
    try:
        result = await svc.sync_bidirectional(
            user_id=current_user.id,
            integration_id=integration.id,
            session=session,
        )
        return SalesforceSyncResult(**result)
    except Exception as e:
        raise HTTPException(502, f"Sync failed: {e}")


@router.get("/field-mappings", response_model=list[SalesforceFieldMappingRead])
async def list_field_mappings(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[SalesforceFieldMappingRead]:
    """List field mappings for the user's Salesforce integration."""
    integration = await _get_sf_integration(current_user.id, session)
    result = await session.execute(
        select(SalesforceFieldMapping).where(
            SalesforceFieldMapping.integration_id == integration.id
        )
    )
    return result.scalars().all()


@router.post("/field-mappings", response_model=SalesforceFieldMappingRead)
async def create_field_mapping(
    payload: SalesforceFieldMappingCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SalesforceFieldMappingRead:
    """Create a new Salesforce field mapping."""
    integration = await _get_sf_integration(current_user.id, session)
    mapping = SalesforceFieldMapping(
        integration_id=integration.id,
        sniper_field=payload.sniper_field,
        salesforce_field=payload.salesforce_field,
        direction=payload.direction,
        transform=payload.transform,
    )
    session.add(mapping)
    await session.commit()
    await session.refresh(mapping)
    return mapping


@router.delete("/field-mappings/{mapping_id}")
async def delete_field_mapping(
    mapping_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Delete a Salesforce field mapping."""
    integration = await _get_sf_integration(current_user.id, session)
    result = await session.execute(
        select(SalesforceFieldMapping).where(
            SalesforceFieldMapping.id == mapping_id,
            SalesforceFieldMapping.integration_id == integration.id,
        )
    )
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise HTTPException(404, "Field mapping not found")
    await session.delete(mapping)
    await session.commit()
    return {"deleted": True}


@router.post("/webhooks/inbound")
async def salesforce_webhook_inbound(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Receive Salesforce outbound messages (webhook).

    This endpoint is unauthenticated because SF outbound messages
    hit it directly. Payload is stored for later processing.
    """
    from app.models.integration import IntegrationWebhookEvent

    try:
        body = await request.json()
    except Exception:
        body = {}

    event = IntegrationWebhookEvent(
        integration_id=0,  # resolved later
        provider=IntegrationProvider.SALESFORCE,
        event_type=body.get("event", "inbound"),
        payload=body,
    )
    session.add(event)
    await session.commit()
    return {"received": True}
