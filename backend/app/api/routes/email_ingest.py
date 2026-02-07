"""Email ingestion configuration and history routes."""

from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.api.deps import get_current_user
from app.services.auth_service import UserAuth
from app.models.email_ingest import EmailIngestConfig, IngestedEmail, ProcessingStatus
from app.schemas.email_ingest import (
    EmailIngestConfigCreate,
    EmailIngestConfigRead,
    EmailIngestConfigUpdate,
    IngestedEmailRead,
    EmailIngestListResponse,
)

router = APIRouter(prefix="/email-ingest", tags=["email-ingest"])


# ---- Config CRUD ----


@router.post("/config", response_model=EmailIngestConfigRead)
async def create_config(
    payload: EmailIngestConfigCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> EmailIngestConfigRead:
    config = EmailIngestConfig(
        user_id=current_user.id,
        imap_server=payload.imap_server,
        imap_port=payload.imap_port,
        email_address=payload.email_address,
        encrypted_password=payload.password,  # TODO: encrypt before storing
        folder=payload.folder,
    )
    session.add(config)
    await session.commit()
    await session.refresh(config)
    return EmailIngestConfigRead.model_validate(config).mask_password()


@router.get("/config", response_model=List[EmailIngestConfigRead])
async def list_configs(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[EmailIngestConfigRead]:
    result = await session.execute(
        select(EmailIngestConfig)
        .where(EmailIngestConfig.user_id == current_user.id)
        .order_by(EmailIngestConfig.created_at.desc())
    )
    configs = result.scalars().all()
    return [
        EmailIngestConfigRead.model_validate(c).mask_password() for c in configs
    ]


@router.patch("/config/{config_id}", response_model=EmailIngestConfigRead)
async def update_config(
    config_id: int,
    payload: EmailIngestConfigUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> EmailIngestConfigRead:
    result = await session.execute(
        select(EmailIngestConfig).where(
            EmailIngestConfig.id == config_id,
            EmailIngestConfig.user_id == current_user.id,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    update_data = payload.model_dump(exclude_unset=True)
    if "password" in update_data:
        config.encrypted_password = update_data.pop("password")  # TODO: encrypt
    for field, value in update_data.items():
        setattr(config, field, value)
    config.updated_at = datetime.utcnow()

    await session.commit()
    await session.refresh(config)
    return EmailIngestConfigRead.model_validate(config).mask_password()


@router.delete("/config/{config_id}")
async def delete_config(
    config_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(
        select(EmailIngestConfig).where(
            EmailIngestConfig.id == config_id,
            EmailIngestConfig.user_id == current_user.id,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    await session.delete(config)
    await session.commit()
    return {"message": "Config deleted"}


@router.post("/config/{config_id}/test")
async def test_connection(
    config_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(
        select(EmailIngestConfig).where(
            EmailIngestConfig.id == config_id,
            EmailIngestConfig.user_id == current_user.id,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    # Mock IMAP connection test for now
    return {"success": True, "message": f"Connection to {config.imap_server} successful (mock)"}


# ---- Ingested email history ----


@router.get("/history", response_model=EmailIngestListResponse)
async def list_history(
    config_id: Optional[int] = None,
    status: Optional[ProcessingStatus] = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> EmailIngestListResponse:
    # Get user's config IDs for authorization
    config_result = await session.execute(
        select(EmailIngestConfig.id).where(
            EmailIngestConfig.user_id == current_user.id
        )
    )
    user_config_ids = [row[0] for row in config_result.fetchall()]

    if not user_config_ids:
        return EmailIngestListResponse(items=[], total=0)

    query = select(IngestedEmail).where(
        IngestedEmail.config_id.in_(user_config_ids)
    )

    if config_id is not None:
        if config_id not in user_config_ids:
            raise HTTPException(status_code=403, detail="Not authorized")
        query = query.where(IngestedEmail.config_id == config_id)
    if status is not None:
        query = query.where(IngestedEmail.processing_status == status)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    query = query.order_by(IngestedEmail.received_at.desc())
    query = query.offset(offset).limit(limit)
    result = await session.execute(query)
    emails = result.scalars().all()

    return EmailIngestListResponse(
        items=[IngestedEmailRead.model_validate(e) for e in emails],
        total=total,
    )


@router.post("/process/{email_id}", response_model=IngestedEmailRead)
async def reprocess_email(
    email_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> IngestedEmailRead:
    # Verify ownership through config
    result = await session.execute(
        select(IngestedEmail).where(IngestedEmail.id == email_id)
    )
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    config_result = await session.execute(
        select(EmailIngestConfig).where(
            EmailIngestConfig.id == email.config_id,
            EmailIngestConfig.user_id == current_user.id,
        )
    )
    if not config_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not authorized")

    # Reset status to pending for reprocessing
    email.processing_status = ProcessingStatus.PENDING
    email.error_message = None
    await session.commit()
    await session.refresh(email)
    return IngestedEmailRead.model_validate(email)
