"""
RFP Sniper - Integrations Routes
================================
CRUD for integration configurations.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.api.deps import get_current_user
from app.services.auth_service import UserAuth
from app.models.integration import IntegrationConfig, IntegrationProvider
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/integrations", tags=["Integrations"])


class IntegrationCreate(BaseModel):
    provider: IntegrationProvider
    name: Optional[str] = None
    is_enabled: bool = True
    config: dict = {}


class IntegrationUpdate(BaseModel):
    name: Optional[str] = None
    is_enabled: Optional[bool] = None
    config: Optional[dict] = None


class IntegrationResponse(BaseModel):
    id: int
    provider: IntegrationProvider
    name: Optional[str]
    is_enabled: bool
    config: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


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
