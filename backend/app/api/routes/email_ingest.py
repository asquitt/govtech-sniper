"""Email ingestion configuration and history routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.collaboration import SharedWorkspace, WorkspaceMember
from app.models.email_ingest import EmailIngestConfig, EmailProcessingStatus, IngestedEmail
from app.schemas.email_ingest import (
    EmailIngestConfigCreate,
    EmailIngestConfigRead,
    EmailIngestConfigUpdate,
    EmailIngestListResponse,
    EmailIngestSyncRequest,
    EmailIngestSyncResponse,
    IngestedEmailRead,
)
from app.services.auth_service import UserAuth
from app.services.email_ingest_service import EmailIngestService
from app.services.encryption_service import decrypt_value, encrypt_value
from app.tasks.email_ingest_tasks import poll_email_configs, process_pending_ingested_emails

router = APIRouter(prefix="/email-ingest", tags=["email-ingest"])


# ---- Config CRUD ----


async def _ensure_workspace_access(
    *,
    workspace_id: int | None,
    current_user: UserAuth,
    session: AsyncSession,
) -> None:
    if workspace_id is None:
        return

    workspace = await session.get(SharedWorkspace, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    if workspace.owner_id == current_user.id:
        return

    member_result = await session.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == current_user.id,
        )
    )
    if not member_result.scalars().first():
        raise HTTPException(status_code=403, detail="Not authorized for workspace")


@router.post("/config", response_model=EmailIngestConfigRead)
async def create_config(
    payload: EmailIngestConfigCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> EmailIngestConfigRead:
    await _ensure_workspace_access(
        workspace_id=payload.workspace_id,
        current_user=current_user,
        session=session,
    )
    config = EmailIngestConfig(
        user_id=current_user.id,
        workspace_id=payload.workspace_id,
        imap_server=payload.imap_server,
        imap_port=payload.imap_port,
        email_address=payload.email_address,
        encrypted_password=encrypt_value(payload.password),
        folder=payload.folder,
        auto_create_rfps=payload.auto_create_rfps,
        min_rfp_confidence=payload.min_rfp_confidence,
    )
    session.add(config)
    await session.commit()
    await session.refresh(config)
    return EmailIngestConfigRead.model_validate(config).mask_password()


@router.get("/config", response_model=list[EmailIngestConfigRead])
async def list_configs(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[EmailIngestConfigRead]:
    result = await session.execute(
        select(EmailIngestConfig)
        .where(EmailIngestConfig.user_id == current_user.id)
        .order_by(EmailIngestConfig.created_at.desc())
    )
    configs = result.scalars().all()
    return [EmailIngestConfigRead.model_validate(c).mask_password() for c in configs]


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
    if "workspace_id" in update_data:
        await _ensure_workspace_access(
            workspace_id=update_data.get("workspace_id"),
            current_user=current_user,
            session=session,
        )
    if "password" in update_data:
        config.encrypted_password = encrypt_value(update_data.pop("password"))
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

    password = decrypt_value(config.encrypted_password)
    service = EmailIngestService(
        host=config.imap_server,
        port=config.imap_port,
        username=config.email_address,
        password=password,
        use_ssl=config.imap_port == 993,
    )
    test_result = await service.test_connection()
    if test_result.get("status") == "connected":
        return {
            "success": True,
            "message": f"Connected to {config.imap_server}",
            "folders": test_result.get("folders", []),
        }
    raise HTTPException(status_code=400, detail=test_result.get("message", "Connection failed"))


# ---- Ingested email history ----


@router.get("/history", response_model=EmailIngestListResponse)
async def list_history(
    config_id: int | None = None,
    status: EmailProcessingStatus | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> EmailIngestListResponse:
    # Get user's config IDs for authorization
    config_result = await session.execute(
        select(EmailIngestConfig.id).where(EmailIngestConfig.user_id == current_user.id)
    )
    user_config_ids = [row[0] for row in config_result.fetchall()]

    if not user_config_ids:
        return EmailIngestListResponse(items=[], total=0)

    query = select(IngestedEmail).where(IngestedEmail.config_id.in_(user_config_ids))

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
    result = await session.execute(select(IngestedEmail).where(IngestedEmail.id == email_id))
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
    email.processing_status = EmailProcessingStatus.PENDING
    email.error_message = None
    await session.commit()
    await session.refresh(email)
    return IngestedEmailRead.model_validate(email)


@router.post("/sync-now", response_model=EmailIngestSyncResponse)
async def sync_now(
    payload: EmailIngestSyncRequest,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> EmailIngestSyncResponse:
    query = select(EmailIngestConfig).where(EmailIngestConfig.user_id == current_user.id)
    if payload.config_id is not None:
        query = query.where(EmailIngestConfig.id == payload.config_id)

    configs = (await session.execute(query)).scalars().all()
    if payload.config_id is not None and not configs:
        raise HTTPException(status_code=404, detail="Config not found")
    if not configs:
        return EmailIngestSyncResponse(
            configs_checked=0,
            fetched=0,
            duplicates=0,
            poll_errors=0,
            processed=0,
            created_rfps=0,
            inbox_forwarded=0,
            process_errors=0,
        )

    poll_summary = {"configs_checked": len(configs), "fetched": 0, "duplicates": 0, "errors": 0}
    if payload.run_poll:
        poll_summary = await poll_email_configs(
            session,
            configs=configs,
            limit=payload.poll_limit,
        )

    process_summary = {"processed": 0, "created_rfps": 0, "inbox_forwarded": 0, "errors": 0}
    if payload.run_process:
        process_summary = await process_pending_ingested_emails(
            session,
            config_ids=[config.id for config in configs],
            limit=payload.process_limit,
        )

    await session.commit()
    return EmailIngestSyncResponse(
        configs_checked=poll_summary["configs_checked"],
        fetched=poll_summary["fetched"],
        duplicates=poll_summary["duplicates"],
        poll_errors=poll_summary["errors"],
        processed=process_summary["processed"],
        created_rfps=process_summary["created_rfps"],
        inbox_forwarded=process_summary["inbox_forwarded"],
        process_errors=process_summary["errors"],
    )
