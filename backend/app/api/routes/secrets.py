"""
RFP Sniper - Secrets Vault Routes
================================
Encrypted secrets storage with audit logging.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.secret import SecretRecord
from app.services.audit_service import log_audit_event
from app.services.auth_service import UserAuth
from app.services.encryption_service import decrypt_value, encrypt_value, redact_value

router = APIRouter(prefix="/secrets", tags=["Secrets"])


class SecretCreate(BaseModel):
    key: str = Field(min_length=2, max_length=255)
    value: str = Field(min_length=1, max_length=2000)


class SecretResponse(BaseModel):
    id: int
    key: str
    value: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


@router.get("", response_model=list[SecretResponse])
async def list_secrets(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[SecretResponse]:
    result = await session.execute(
        select(SecretRecord).where(SecretRecord.user_id == current_user.id)
    )
    secrets = result.scalars().all()
    return [
        SecretResponse(
            id=record.id,
            key=record.key,
            value=redact_value("secret"),
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
        for record in secrets
    ]


@router.post("", response_model=SecretResponse)
async def create_or_update_secret(
    payload: SecretCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SecretResponse:
    result = await session.execute(
        select(SecretRecord).where(
            SecretRecord.user_id == current_user.id,
            SecretRecord.key == payload.key,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        record = SecretRecord(
            user_id=current_user.id,
            key=payload.key,
            value_encrypted=encrypt_value(payload.value),
        )
        session.add(record)
        await session.flush()
        action = "secret.created"
    else:
        record.value_encrypted = encrypt_value(payload.value)
        record.updated_at = datetime.utcnow()
        action = "secret.updated"

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="secret",
        entity_id=record.id,
        action=action,
        metadata={"key": payload.key},
    )
    await session.commit()
    await session.refresh(record)
    return SecretResponse(
        id=record.id,
        key=record.key,
        value=redact_value("secret"),
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.get("/{secret_key}", response_model=SecretResponse)
async def get_secret(
    secret_key: str,
    reveal: bool = Query(False),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SecretResponse:
    result = await session.execute(
        select(SecretRecord).where(
            SecretRecord.user_id == current_user.id,
            SecretRecord.key == secret_key,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Secret not found")

    value = decrypt_value(record.value_encrypted) if reveal else redact_value("secret")
    return SecretResponse(
        id=record.id,
        key=record.key,
        value=value,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.delete("/{secret_key}")
async def delete_secret(
    secret_key: str,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    result = await session.execute(
        select(SecretRecord).where(
            SecretRecord.user_id == current_user.id,
            SecretRecord.key == secret_key,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Secret not found")

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="secret",
        entity_id=record.id,
        action="secret.deleted",
        metadata={"key": secret_key},
    )
    await session.delete(record)
    await session.commit()
    return {"message": "Secret deleted"}
