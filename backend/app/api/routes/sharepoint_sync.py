"""
RFP Sniper - SharePoint Sync Routes
=====================================
Configure, trigger, and monitor SharePoint auto-sync for proposals.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import check_rate_limit, get_current_user
from app.database import get_session
from app.models.sharepoint_sync import SharePointSyncConfig, SharePointSyncLog, SyncDirection
from app.services.auth_service import UserAuth

router = APIRouter(prefix="/sharepoint/sync", tags=["SharePoint Sync"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class SyncConfigCreate(BaseModel):
    proposal_id: int
    sharepoint_folder: str
    sync_direction: SyncDirection = SyncDirection.PUSH
    auto_sync_enabled: bool = False
    watch_for_rfps: bool = False


class SyncConfigUpdate(BaseModel):
    sharepoint_folder: str | None = None
    sync_direction: SyncDirection | None = None
    auto_sync_enabled: bool | None = None
    watch_for_rfps: bool | None = None


class SyncConfigRead(BaseModel):
    id: int
    user_id: int
    proposal_id: int
    sharepoint_folder: str
    sync_direction: SyncDirection
    auto_sync_enabled: bool
    watch_for_rfps: bool
    last_synced_at: str | None = None
    created_at: str
    updated_at: str


class SyncLogRead(BaseModel):
    id: int
    config_id: int
    action: str
    status: str
    details: dict
    created_at: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/configure", response_model=SyncConfigRead)
async def configure_sync(
    payload: SyncConfigCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(check_rate_limit),
) -> SyncConfigRead:
    """Create or update a SharePoint sync configuration for a proposal."""
    # Check for existing config
    result = await session.execute(
        select(SharePointSyncConfig).where(
            SharePointSyncConfig.user_id == current_user.id,
            SharePointSyncConfig.proposal_id == payload.proposal_id,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.sharepoint_folder = payload.sharepoint_folder
        existing.sync_direction = payload.sync_direction
        existing.auto_sync_enabled = payload.auto_sync_enabled
        existing.watch_for_rfps = payload.watch_for_rfps
        existing.updated_at = datetime.utcnow()
        session.add(existing)
        await session.commit()
        await session.refresh(existing)
        return _to_read(existing)

    config = SharePointSyncConfig(
        user_id=current_user.id,
        proposal_id=payload.proposal_id,
        sharepoint_folder=payload.sharepoint_folder,
        sync_direction=payload.sync_direction,
        auto_sync_enabled=payload.auto_sync_enabled,
        watch_for_rfps=payload.watch_for_rfps,
    )
    session.add(config)
    await session.commit()
    await session.refresh(config)
    return _to_read(config)


@router.get("/configs", response_model=list[SyncConfigRead])
async def list_sync_configs(
    proposal_id: int | None = Query(None),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[SyncConfigRead]:
    """List sync configurations for the current user."""
    stmt = select(SharePointSyncConfig).where(
        SharePointSyncConfig.user_id == current_user.id,
    )
    if proposal_id is not None:
        stmt = stmt.where(SharePointSyncConfig.proposal_id == proposal_id)
    result = await session.execute(stmt)
    return [_to_read(c) for c in result.scalars().all()]


@router.post("/{config_id}/trigger")
async def trigger_sync(
    config_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(check_rate_limit),
) -> dict:
    """Manually trigger a sync for a configuration."""
    config = await _get_user_config(config_id, current_user.id, session)

    from app.tasks.sharepoint_sync_tasks import sync_proposal_to_sharepoint

    task = sync_proposal_to_sharepoint.delay(config.id)
    return {"task_id": task.id, "message": "Sync triggered", "config_id": config.id}


@router.get("/{config_id}/status", response_model=list[SyncLogRead])
async def get_sync_status(
    config_id: int,
    limit: int = Query(20, ge=1, le=100),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[SyncLogRead]:
    """Get sync logs for a configuration."""
    await _get_user_config(config_id, current_user.id, session)

    result = await session.execute(
        select(SharePointSyncLog)
        .where(SharePointSyncLog.config_id == config_id)
        .order_by(SharePointSyncLog.created_at.desc())
        .limit(limit)
    )
    return [
        SyncLogRead(
            id=log.id,
            config_id=log.config_id,
            action=log.action,
            status=log.status,
            details=log.details,
            created_at=log.created_at.isoformat(),
        )
        for log in result.scalars().all()
    ]


@router.delete("/{config_id}")
async def delete_sync_config(
    config_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Delete a sync configuration."""
    config = await _get_user_config(config_id, current_user.id, session)
    await session.delete(config)
    await session.commit()
    return {"message": "Sync config deleted", "config_id": config_id}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_user_config(
    config_id: int, user_id: int, session: AsyncSession
) -> SharePointSyncConfig:
    result = await session.execute(
        select(SharePointSyncConfig).where(
            SharePointSyncConfig.id == config_id,
            SharePointSyncConfig.user_id == user_id,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(404, "Sync config not found")
    return config


def _to_read(config: SharePointSyncConfig) -> SyncConfigRead:
    return SyncConfigRead(
        id=config.id,
        user_id=config.user_id,
        proposal_id=config.proposal_id,
        sharepoint_folder=config.sharepoint_folder,
        sync_direction=config.sync_direction,
        auto_sync_enabled=config.auto_sync_enabled,
        watch_for_rfps=config.watch_for_rfps,
        last_synced_at=config.last_synced_at.isoformat() if config.last_synced_at else None,
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat(),
    )
