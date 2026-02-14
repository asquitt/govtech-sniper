"""
RFP Sniper - Unanet Integration Routes
========================================
Project sync, status, and listing for Unanet ERP integration.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.integration import IntegrationConfig, IntegrationProvider
from app.services.auth_service import UserAuth
from app.services.unanet_service import UnanetService, UnanetServiceError

router = APIRouter(prefix="/unanet", tags=["unanet"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_unanet_integration(user_id: int, session: AsyncSession) -> IntegrationConfig | None:
    """Load the user's Unanet integration config."""
    result = await session.execute(
        select(IntegrationConfig).where(
            IntegrationConfig.user_id == user_id,
            IntegrationConfig.provider == IntegrationProvider.UNANET,
        )
    )
    return result.scalar_one_or_none()


def _endpoint_configured(config_data: dict, key: str) -> bool:
    if key not in config_data:
        return False
    value = config_data.get(key)
    if isinstance(value, str):
        return bool(value.strip())
    return bool(value)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/status")
async def unanet_status(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Check if Unanet integration is configured and enabled."""
    config = await _get_unanet_integration(current_user.id, session)
    if not config:
        return {"configured": False, "enabled": False}
    config_data = config.config if isinstance(config.config, dict) else {}
    healthy = None
    if config.is_enabled:
        service = UnanetService(config)
        healthy = await service.health_check()
    return {
        "configured": True,
        "enabled": config.is_enabled,
        "base_url": config_data.get("base_url"),
        "healthy": healthy,
        "resources_supported": _endpoint_configured(config_data, "resources_endpoint"),
        "financials_supported": _endpoint_configured(config_data, "financials_endpoint"),
    }


@router.post("/sync")
async def unanet_sync(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Trigger a project sync with Unanet."""
    config = await _get_unanet_integration(current_user.id, session)
    if not config or not config.is_enabled:
        raise HTTPException(404, "Unanet integration not configured or disabled")
    svc = UnanetService(config)
    try:
        return await svc.sync_projects()
    except UnanetServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/projects")
async def unanet_projects(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    """List projects from Unanet."""
    config = await _get_unanet_integration(current_user.id, session)
    if not config or not config.is_enabled:
        raise HTTPException(404, "Unanet integration not configured or disabled")
    svc = UnanetService(config)
    try:
        return await svc.list_projects()
    except UnanetServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/resources")
async def unanet_resources(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    """List resource planning records from Unanet."""
    config = await _get_unanet_integration(current_user.id, session)
    if not config or not config.is_enabled:
        raise HTTPException(404, "Unanet integration not configured or disabled")
    svc = UnanetService(config)
    try:
        return await svc.list_resources()
    except UnanetServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/financials")
async def unanet_financials(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    """List contract financial records from Unanet."""
    config = await _get_unanet_integration(current_user.id, session)
    if not config or not config.is_enabled:
        raise HTTPException(404, "Unanet integration not configured or disabled")
    svc = UnanetService(config)
    try:
        return await svc.list_financials()
    except UnanetServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/sync/resources")
async def unanet_sync_resources(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Trigger a resource planning sync with Unanet."""
    config = await _get_unanet_integration(current_user.id, session)
    if not config or not config.is_enabled:
        raise HTTPException(404, "Unanet integration not configured or disabled")
    svc = UnanetService(config)
    try:
        return await svc.sync_resources()
    except UnanetServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/sync/financials")
async def unanet_sync_financials(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Trigger a financial record sync with Unanet."""
    config = await _get_unanet_integration(current_user.id, session)
    if not config or not config.is_enabled:
        raise HTTPException(404, "Unanet integration not configured or disabled")
    svc = UnanetService(config)
    try:
        return await svc.sync_financials()
    except UnanetServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
