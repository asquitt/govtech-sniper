"""
RFP Sniper - Dash Routes
========================
Minimal Dash (AI assistant) endpoints.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.api.deps import get_current_user
from app.services.auth_service import UserAuth
from app.models.dash import DashSession, DashMessage, DashRole
from app.services.dash_service import generate_dash_response
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/dash", tags=["Dash"])


class DashSessionCreate(BaseModel):
    title: Optional[str] = None


class DashSessionResponse(BaseModel):
    id: int
    title: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DashMessageCreate(BaseModel):
    role: DashRole = DashRole.USER
    content: str


class DashMessageResponse(BaseModel):
    id: int
    session_id: int
    role: DashRole
    content: str
    citations: List[dict]
    created_at: datetime

    model_config = {"from_attributes": True}


class DashAskRequest(BaseModel):
    question: str
    rfp_id: Optional[int] = None


class DashAskResponse(BaseModel):
    answer: str
    citations: List[dict]


class DashRunbookRequest(BaseModel):
    rfp_id: Optional[int] = None


class DashRunbookResponse(BaseModel):
    runbook: str
    answer: str
    citations: List[dict]


RUNBOOK_PROMPTS = {
    "rfp_summary": "Summarize this opportunity with key details.",
    "compliance_gap_plan": "Summarize compliance gaps and next steps.",
    "proposal_kickoff": "Provide a proposal kickoff plan and stakeholder checklist.",
    "competitive_intel": "Summarize competitive intelligence for this opportunity.",
}


@router.get("/sessions", response_model=List[DashSessionResponse])
async def list_sessions(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[DashSessionResponse]:
    result = await session.execute(
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
    session: AsyncSession = Depends(get_session),
) -> DashSessionResponse:
    dash_session = DashSession(
        user_id=current_user.id,
        title=payload.title,
    )
    session.add(dash_session)
    await session.flush()
    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="dash_session",
        entity_id=dash_session.id,
        action="dash.session_created",
        metadata={"title": dash_session.title},
    )
    await session.commit()
    await session.refresh(dash_session)

    return DashSessionResponse.model_validate(dash_session)


@router.post("/sessions/{session_id}/messages", response_model=DashMessageResponse)
async def add_message(
    session_id: int,
    payload: DashMessageCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DashMessageResponse:
    # Ensure session ownership
    result = await session.execute(
        select(DashSession).where(
            DashSession.id == session_id,
            DashSession.user_id == current_user.id,
        )
    )
    dash_session = result.scalar_one_or_none()
    if not dash_session:
        raise HTTPException(status_code=404, detail="Dash session not found")

    message = DashMessage(
        session_id=session_id,
        role=payload.role,
        content=payload.content,
        citations=[],
    )
    session.add(message)
    await session.flush()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="dash_message",
        entity_id=message.id,
        action="dash.message_created",
        metadata={"role": message.role.value},
    )

    await session.commit()
    await session.refresh(message)

    return DashMessageResponse.model_validate(message)


@router.post("/ask", response_model=DashAskResponse)
async def ask_dash(
    payload: DashAskRequest,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DashAskResponse:
    answer, citations = await generate_dash_response(
        session,
        user_id=current_user.id,
        question=payload.question,
        rfp_id=payload.rfp_id,
    )

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="dash",
        entity_id=None,
        action="dash.asked",
        metadata={"question": payload.question, "rfp_id": payload.rfp_id},
    )
    await session.commit()

    return DashAskResponse(answer=answer, citations=citations)


@router.post("/runbooks/{runbook}", response_model=DashRunbookResponse)
async def run_dash_runbook(
    runbook: str,
    payload: DashRunbookRequest,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DashRunbookResponse:
    if runbook not in RUNBOOK_PROMPTS:
        raise HTTPException(status_code=404, detail="Runbook not found")

    answer, citations = await generate_dash_response(
        session,
        user_id=current_user.id,
        question=RUNBOOK_PROMPTS[runbook],
        rfp_id=payload.rfp_id,
    )

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="dash_runbook",
        entity_id=None,
        action="dash.runbook_executed",
        metadata={"runbook": runbook, "rfp_id": payload.rfp_id},
    )
    await session.commit()

    return DashRunbookResponse(runbook=runbook, answer=answer, citations=citations)
