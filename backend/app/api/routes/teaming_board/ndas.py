"""Teaming Board - NDA Tracking."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.capture import NDAStatus, TeamingNDA
from app.schemas.teaming import NDACreate, NDARead, NDAUpdate
from app.services.auth_service import UserAuth

router = APIRouter()


@router.post("/ndas", response_model=NDARead, status_code=201)
async def create_nda(
    payload: NDACreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> NDARead:
    """Create an NDA record."""
    nda = TeamingNDA(
        user_id=current_user.id,
        partner_id=payload.partner_id,
        rfp_id=payload.rfp_id,
        document_path=payload.document_path,
        notes=payload.notes,
    )
    if payload.signed_date:
        nda.signed_date = datetime.strptime(payload.signed_date, "%Y-%m-%d").date()
    if payload.expiry_date:
        nda.expiry_date = datetime.strptime(payload.expiry_date, "%Y-%m-%d").date()
    session.add(nda)
    await session.commit()
    await session.refresh(nda)
    return NDARead.model_validate(nda)


@router.get("/ndas", response_model=list[NDARead])
async def list_ndas(
    partner_id: int | None = Query(None),
    status: str | None = Query(None),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[NDARead]:
    """List NDAs for the current user."""
    stmt = select(TeamingNDA).where(TeamingNDA.user_id == current_user.id)
    if partner_id:
        stmt = stmt.where(TeamingNDA.partner_id == partner_id)
    if status:
        stmt = stmt.where(TeamingNDA.status == NDAStatus(status))
    stmt = stmt.order_by(TeamingNDA.created_at.desc())
    result = await session.execute(stmt)
    return [NDARead.model_validate(n) for n in result.scalars().all()]


@router.patch("/ndas/{nda_id}", response_model=NDARead)
async def update_nda(
    nda_id: int,
    payload: NDAUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> NDARead:
    """Update NDA status or details."""
    nda = await session.get(TeamingNDA, nda_id)
    if not nda or nda.user_id != current_user.id:
        raise HTTPException(404, "NDA not found")
    if payload.status is not None:
        nda.status = NDAStatus(payload.status)
    if payload.signed_date is not None:
        nda.signed_date = datetime.strptime(payload.signed_date, "%Y-%m-%d").date()
    if payload.expiry_date is not None:
        nda.expiry_date = datetime.strptime(payload.expiry_date, "%Y-%m-%d").date()
    if payload.document_path is not None:
        nda.document_path = payload.document_path
    if payload.notes is not None:
        nda.notes = payload.notes
    nda.updated_at = datetime.utcnow()
    session.add(nda)
    await session.commit()
    await session.refresh(nda)
    return NDARead.model_validate(nda)
