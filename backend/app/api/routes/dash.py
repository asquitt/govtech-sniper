"""
RFP Sniper - Dash Routes
========================
AI-powered chat assistant with streaming and session management.
"""

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from sse_starlette.sse import EventSourceResponse

from app.api.deps import check_rate_limit, get_current_user
from app.database import get_session
from app.models.dash import DashMessage, DashRole, DashSession
from app.services.audit_service import log_audit_event
from app.services.auth_service import UserAuth
from app.services.dash_service import (
    generate_dash_response,
    generate_dash_response_stream,
    get_context_citations,
)

router = APIRouter(prefix="/dash", tags=["Dash"])


# =============================================================================
# Schemas
# =============================================================================


class DashSessionCreate(BaseModel):
    title: str | None = None


class DashSessionResponse(BaseModel):
    id: int
    title: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DashMessageResponse(BaseModel):
    id: int
    session_id: int
    role: DashRole
    content: str
    citations: list[dict]
    created_at: datetime

    model_config = {"from_attributes": True}


class DashAskRequest(BaseModel):
    question: str
    rfp_id: int | None = None
    session_id: int | None = None


class DashAskResponse(BaseModel):
    answer: str
    citations: list[dict]
    message_id: int | None = None


class DashChatRequest(BaseModel):
    question: str
    rfp_id: int | None = None
    session_id: int | None = None


# =============================================================================
# Session endpoints
# =============================================================================


@router.get("/sessions", response_model=list[DashSessionResponse])
async def list_sessions(
    current_user: UserAuth = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> list[DashSessionResponse]:
    result = await db.execute(
        select(DashSession)
        .where(DashSession.user_id == current_user.id)
        .order_by(DashSession.created_at.desc())
    )
    sessions = result.scalars().all()
    return [DashSessionResponse.model_validate(s) for s in sessions]


@router.post("/sessions", response_model=DashSessionResponse)
async def create_session(
    payload: DashSessionCreate,
    current_user: UserAuth = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> DashSessionResponse:
    dash_session = DashSession(user_id=current_user.id, title=payload.title)
    db.add(dash_session)
    await db.flush()
    await log_audit_event(
        db,
        user_id=current_user.id,
        entity_type="dash_session",
        entity_id=dash_session.id,
        action="dash.session_created",
        metadata={"title": dash_session.title},
    )
    await db.commit()
    await db.refresh(dash_session)
    return DashSessionResponse.model_validate(dash_session)


@router.get("/sessions/{session_id}/messages", response_model=list[DashMessageResponse])
async def get_session_messages(
    session_id: int,
    current_user: UserAuth = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> list[DashMessageResponse]:
    # Verify ownership
    result = await db.execute(
        select(DashSession).where(
            DashSession.id == session_id, DashSession.user_id == current_user.id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Dash session not found")

    msg_result = await db.execute(
        select(DashMessage)
        .where(DashMessage.session_id == session_id)
        .order_by(DashMessage.created_at.asc())
    )
    messages = msg_result.scalars().all()
    return [DashMessageResponse.model_validate(m) for m in messages]


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: int,
    current_user: UserAuth = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    result = await db.execute(
        select(DashSession).where(
            DashSession.id == session_id, DashSession.user_id == current_user.id
        )
    )
    dash_session = result.scalar_one_or_none()
    if not dash_session:
        raise HTTPException(status_code=404, detail="Dash session not found")

    # Delete messages first, then session
    msg_result = await db.execute(select(DashMessage).where(DashMessage.session_id == session_id))
    for msg in msg_result.scalars().all():
        await db.delete(msg)
    await db.delete(dash_session)
    await db.commit()
    return {"ok": True}


# =============================================================================
# Chat endpoints
# =============================================================================


async def _load_conversation_history(db: AsyncSession, session_id: int, user_id: int) -> list[dict]:
    """Load conversation history from a session."""
    result = await db.execute(
        select(DashSession).where(DashSession.id == session_id, DashSession.user_id == user_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Dash session not found")

    msg_result = await db.execute(
        select(DashMessage)
        .where(DashMessage.session_id == session_id)
        .order_by(DashMessage.created_at.asc())
    )
    messages = msg_result.scalars().all()
    return [{"role": m.role.value, "content": m.content} for m in messages]


async def _persist_exchange(
    db: AsyncSession,
    session_id: int,
    question: str,
    answer: str,
    citations: list[dict],
) -> int:
    """Save user question and assistant answer to session. Returns assistant message id."""
    # Auto-title on first message
    result = await db.execute(select(DashSession).where(DashSession.id == session_id))
    dash_session = result.scalar_one_or_none()
    if dash_session and not dash_session.title:
        dash_session.title = question[:80]
        db.add(dash_session)

    user_msg = DashMessage(
        session_id=session_id,
        role=DashRole.USER,
        content=question,
        citations=[],
    )
    db.add(user_msg)

    assistant_msg = DashMessage(
        session_id=session_id,
        role=DashRole.ASSISTANT,
        content=answer,
        citations=citations,
    )
    db.add(assistant_msg)
    await db.flush()
    msg_id = assistant_msg.id
    await db.commit()
    return msg_id


@router.post("/ask", response_model=DashAskResponse, dependencies=[Depends(check_rate_limit)])
async def ask_dash(
    payload: DashAskRequest,
    current_user: UserAuth = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> DashAskResponse:
    conversation_history = None
    if payload.session_id:
        conversation_history = await _load_conversation_history(
            db, payload.session_id, current_user.id
        )

    answer, citations = await generate_dash_response(
        db,
        user_id=current_user.id,
        question=payload.question,
        rfp_id=payload.rfp_id,
        conversation_history=conversation_history,
    )

    message_id = None
    if payload.session_id:
        message_id = await _persist_exchange(
            db, payload.session_id, payload.question, answer, citations
        )

    await log_audit_event(
        db,
        user_id=current_user.id,
        entity_type="dash",
        entity_id=None,
        action="dash.asked",
        metadata={"question": payload.question, "rfp_id": payload.rfp_id},
    )
    await db.commit()

    return DashAskResponse(answer=answer, citations=citations, message_id=message_id)


@router.post("/chat", dependencies=[Depends(check_rate_limit)])
async def chat_dash_stream(
    payload: DashChatRequest,
    current_user: UserAuth = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> EventSourceResponse:
    """Streaming chat endpoint. Returns SSE events with text chunks."""
    conversation_history = None
    if payload.session_id:
        conversation_history = await _load_conversation_history(
            db, payload.session_id, current_user.id
        )

    # Capture these for the generator closure
    user_id = current_user.id
    rfp_id = payload.rfp_id
    session_id = payload.session_id
    question = payload.question

    async def event_generator():
        full_text = ""
        async for chunk in generate_dash_response_stream(
            db,
            user_id=user_id,
            question=question,
            rfp_id=rfp_id,
            conversation_history=conversation_history,
        ):
            full_text += chunk
            yield {"event": "chunk", "data": json.dumps({"content": chunk})}

        # Get citations and persist
        citations = await get_context_citations(db, user_id=user_id, rfp_id=rfp_id)
        message_id = None
        if session_id:
            message_id = await _persist_exchange(db, session_id, question, full_text, citations)

        yield {
            "event": "done",
            "data": json.dumps(
                {
                    "citations": citations,
                    "message_id": message_id,
                    "full_text": full_text,
                }
            ),
        }

    return EventSourceResponse(event_generator())
