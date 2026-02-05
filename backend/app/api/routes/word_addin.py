"""
RFP Sniper - Word Add-in Routes
===============================
Scaffolding for Word add-in session management.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.api.deps import get_current_user
from app.services.auth_service import UserAuth
from app.models.word_addin import WordAddinSession, WordAddinEvent, WordAddinSessionStatus
from app.models.proposal import Proposal
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/word-addin", tags=["Word Add-in"])


class WordAddinSessionCreate(BaseModel):
    proposal_id: int
    document_name: str
    metadata: Optional[dict] = None


class WordAddinSessionUpdate(BaseModel):
    document_name: Optional[str] = None
    status: Optional[WordAddinSessionStatus] = None
    metadata: Optional[dict] = None


class WordAddinSessionResponse(BaseModel):
    id: int
    proposal_id: int
    document_name: str
    status: WordAddinSessionStatus
    metadata: dict = Field(alias="session_metadata")
    last_synced_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class WordAddinEventCreate(BaseModel):
    event_type: str
    payload: Optional[dict] = None


class WordAddinEventResponse(BaseModel):
    id: int
    session_id: int
    event_type: str
    payload: dict
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/sessions", response_model=List[WordAddinSessionResponse])
async def list_sessions(
    proposal_id: Optional[int] = Query(None),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[WordAddinSessionResponse]:
    query = select(WordAddinSession).where(WordAddinSession.user_id == current_user.id)
    if proposal_id:
        query = query.where(WordAddinSession.proposal_id == proposal_id)
    result = await session.execute(query)
    sessions = result.scalars().all()
    return [WordAddinSessionResponse.model_validate(item) for item in sessions]


@router.post("/sessions", response_model=WordAddinSessionResponse)
async def create_session(
    payload: WordAddinSessionCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WordAddinSessionResponse:
    proposal_result = await session.execute(
        select(Proposal).where(
            Proposal.id == payload.proposal_id,
            Proposal.user_id == current_user.id,
        )
    )
    if not proposal_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Proposal not found")

    session_record = WordAddinSession(
        user_id=current_user.id,
        proposal_id=payload.proposal_id,
        document_name=payload.document_name,
        session_metadata=payload.metadata or {},
    )
    session.add(session_record)
    await session.flush()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="word_addin_session",
        entity_id=session_record.id,
        action="word_addin.session_created",
        metadata={"proposal_id": payload.proposal_id},
    )
    await session.commit()
    await session.refresh(session_record)

    return WordAddinSessionResponse.model_validate(session_record)


@router.patch("/sessions/{session_id}", response_model=WordAddinSessionResponse)
async def update_session(
    session_id: int,
    payload: WordAddinSessionUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WordAddinSessionResponse:
    result = await session.execute(
        select(WordAddinSession).where(
            WordAddinSession.id == session_id,
            WordAddinSession.user_id == current_user.id,
        )
    )
    session_record = result.scalar_one_or_none()
    if not session_record:
        raise HTTPException(status_code=404, detail="Session not found")

    update_data = payload.model_dump(exclude_unset=True)
    if "metadata" in update_data:
        update_data["session_metadata"] = update_data.pop("metadata")
    for key, value in update_data.items():
        setattr(session_record, key, value)
    session_record.updated_at = datetime.utcnow()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="word_addin_session",
        entity_id=session_record.id,
        action="word_addin.session_updated",
        metadata={"updated_fields": list(update_data.keys())},
    )
    await session.commit()
    await session.refresh(session_record)

    return WordAddinSessionResponse.model_validate(session_record)


@router.post("/sessions/{session_id}/events", response_model=WordAddinEventResponse)
async def create_event(
    session_id: int,
    payload: WordAddinEventCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WordAddinEventResponse:
    result = await session.execute(
        select(WordAddinSession).where(
            WordAddinSession.id == session_id,
            WordAddinSession.user_id == current_user.id,
        )
    )
    session_record = result.scalar_one_or_none()
    if not session_record:
        raise HTTPException(status_code=404, detail="Session not found")

    event = WordAddinEvent(
        session_id=session_record.id,
        event_type=payload.event_type,
        payload=payload.payload or {},
    )
    session.add(event)
    session_record.last_synced_at = datetime.utcnow()
    session_record.updated_at = datetime.utcnow()
    await session.flush()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="word_addin_event",
        entity_id=event.id,
        action="word_addin.event_created",
        metadata={"event_type": payload.event_type},
    )
    await session.commit()
    await session.refresh(event)

    return WordAddinEventResponse.model_validate(event)


@router.get("/sessions/{session_id}/events", response_model=List[WordAddinEventResponse])
async def list_events(
    session_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[WordAddinEventResponse]:
    result = await session.execute(
        select(WordAddinSession).where(
            WordAddinSession.id == session_id,
            WordAddinSession.user_id == current_user.id,
        )
    )
    session_record = result.scalar_one_or_none()
    if not session_record:
        raise HTTPException(status_code=404, detail="Session not found")

    events_result = await session.execute(
        select(WordAddinEvent)
        .where(WordAddinEvent.session_id == session_id)
        .order_by(WordAddinEvent.created_at.desc())
    )
    events = events_result.scalars().all()
    return [WordAddinEventResponse.model_validate(event) for event in events]
