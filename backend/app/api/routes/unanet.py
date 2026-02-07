"""
RFP Sniper - Unanet Integration Routes
========================================
Project sync, status, and listing for Unanet ERP integration.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.api.deps import get_current_user
from app.services.auth_service import UserAuth
from app.models.integration import IntegrationConfig, IntegrationProvider
from app.services.unanet_service import UnanetService

router = APIRouter(prefix="/unanet", tags=["unanet"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_unanet_integration(
    user_id: int, session: AsyncSession
) -> IntegrationConfig | None:
    """Load the user's Unanet integration config."""
    result = await session.execute(
        select(IntegrationConfig).where(
            IntegrationConfig.user_id == user_id,
            IntegrationConfig.provider == IntegrationProvider.UNANET,
        )
    )
    return result.scalar_one_or_none()


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
    return {
        "configured": True,
        "enabled": config.is_enabled,
        "base_url": (config.config or {}).get("base_url"),
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
    return await svc.sync_projects()


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
    return await svc.list_projects()
