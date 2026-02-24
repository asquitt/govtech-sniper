"""
Integrations Routes - CRUD
===========================
List providers, list/create/update/delete integrations, and test connectivity.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.integration import IntegrationConfig, IntegrationProvider
from app.services.audit_service import log_audit_event
from app.services.auth_service import UserAuth

from .definitions import (
    PROVIDER_DEFINITIONS,
    IntegrationCreate,
    IntegrationProviderDefinition,
    IntegrationResponse,
    IntegrationTestResult,
    IntegrationUpdate,
    get_provider_definition,
    merge_integration_config,
    missing_required_fields,
    prepare_config_for_response,
    prepare_config_for_storage,
    secret_field_keys,
)

router = APIRouter()


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


@router.get("/", response_model=list[IntegrationResponse])
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
        definition = get_provider_definition(integration.provider)
        response.append(
            IntegrationResponse(
                id=integration.id,
                provider=integration.provider,
                name=integration.name,
                is_enabled=integration.is_enabled,
                config=prepare_config_for_response(integration.config, definition),
                created_at=integration.created_at,
                updated_at=integration.updated_at,
            )
        )
    return response


@router.post("/", response_model=IntegrationResponse)
async def create_integration(
    payload: IntegrationCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> IntegrationResponse:
    definition = get_provider_definition(payload.provider)
    config = prepare_config_for_storage(payload.config or {}, definition)
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
        config=prepare_config_for_response(integration.config, definition),
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
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Integration not found")

    definition = get_provider_definition(integration.provider)
    s_fields = secret_field_keys(definition)
    update_data = payload.model_dump(exclude_unset=True)
    if "config" in update_data:
        merged = merge_integration_config(
            integration.config,
            update_data.get("config"),
            s_fields,
        )
        update_data["config"] = prepare_config_for_storage(merged, definition)
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
        config=prepare_config_for_response(integration.config, definition),
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
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Integration not found")

    definition = get_provider_definition(integration.provider)
    missing = missing_required_fields(definition, integration.config)

    if not integration.is_enabled:
        status = "disabled"
        message = "Integration is disabled."
    elif missing:
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
        metadata={"status": status, "missing_fields": missing},
    )
    await session.commit()

    return IntegrationTestResult(
        status=status,
        message=message,
        missing_fields=missing,
        checked_at=datetime.utcnow(),
    )


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
        from fastapi import HTTPException

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
