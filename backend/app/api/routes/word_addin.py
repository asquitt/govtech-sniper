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


# === Section Sync Endpoints ===


class SectionPullResponse(BaseModel):
    section_id: int
    title: str
    content: str
    requirements: list[str] = []
    last_modified: Optional[str] = None


class SectionPushPayload(BaseModel):
    content: str


class ComplianceCheckResult(BaseModel):
    section_id: int
    compliant: bool
    issues: list[str] = []
    suggestions: list[str] = []


class AIRewritePayload(BaseModel):
    content: str
    mode: str = Field(..., description="shorten, expand, or improve")


class AIRewriteResponse(BaseModel):
    original_length: int
    rewritten: str
    rewritten_length: int
    mode: str


@router.post("/sections/{section_id}/pull", response_model=SectionPullResponse)
async def pull_section_content(
    section_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SectionPullResponse:
    """Pull section content for editing in Word."""
    from app.models.proposal import ProposalSection

    result = await session.execute(
        select(ProposalSection).where(ProposalSection.id == section_id)
    )
    section = result.scalar_one_or_none()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    proposal_result = await session.execute(
        select(Proposal).where(
            Proposal.id == section.proposal_id,
            Proposal.user_id == current_user.id,
        )
    )
    if not proposal_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Proposal not found")

    requirements: list[str] = []
    if section.requirement_text:
        requirements = [section.requirement_text]

    # final_content is str, generated_content is JSON dict
    content = section.final_content or ""
    if not content and section.generated_content:
        if isinstance(section.generated_content, dict):
            content = section.generated_content.get("content", "")
        else:
            content = str(section.generated_content)

    return SectionPullResponse(
        section_id=section.id,
        title=section.title,
        content=content,
        requirements=requirements,
        last_modified=section.updated_at.isoformat() if section.updated_at else None,
    )


@router.post("/sections/{section_id}/push")
async def push_section_content(
    section_id: int,
    payload: SectionPushPayload,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Push edited content from Word back to the system."""
    from app.models.proposal import ProposalSection

    result = await session.execute(
        select(ProposalSection).where(ProposalSection.id == section_id)
    )
    section = result.scalar_one_or_none()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    proposal_result = await session.execute(
        select(Proposal).where(
            Proposal.id == section.proposal_id,
            Proposal.user_id == current_user.id,
        )
    )
    if not proposal_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Proposal not found")

    section.final_content = payload.content
    section.updated_at = datetime.utcnow()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="proposal_section",
        entity_id=section.id,
        action="section.pushed_from_word",
        metadata={"content_length": len(payload.content)},
    )
    await session.commit()

    return {"message": "Section updated", "section_id": section.id}


@router.post(
    "/sections/{section_id}/compliance-check",
    response_model=ComplianceCheckResult,
)
async def check_section_compliance(
    section_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ComplianceCheckResult:
    """Check section content against its requirements."""
    from app.models.proposal import ProposalSection

    result = await session.execute(
        select(ProposalSection).where(ProposalSection.id == section_id)
    )
    section = result.scalar_one_or_none()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    proposal_result = await session.execute(
        select(Proposal).where(
            Proposal.id == section.proposal_id,
            Proposal.user_id == current_user.id,
        )
    )
    if not proposal_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Proposal not found")

    content = section.final_content or ""
    if not content and section.generated_content:
        if isinstance(section.generated_content, dict):
            content = section.generated_content.get("content", "")
        else:
            content = str(section.generated_content)
    requirements: list[str] = []
    if isinstance(section.requirement_text, str) and section.requirement_text:
        requirements = [section.requirement_text]

    issues: list[str] = []
    suggestions: list[str] = []

    if not content.strip():
        issues.append("Section has no content")

    if len(content) < 100 and requirements:
        issues.append("Content appears too short for the requirements")

    for req in requirements:
        req_lower = req.lower()
        if req_lower not in content.lower():
            keyword = req_lower[:50]
            suggestions.append(f"Consider addressing: {keyword}")

    return ComplianceCheckResult(
        section_id=section.id,
        compliant=len(issues) == 0,
        issues=issues,
        suggestions=suggestions[:10],
    )


@router.post("/ai/rewrite", response_model=AIRewriteResponse)
async def ai_rewrite(
    payload: AIRewritePayload,
    current_user: UserAuth = Depends(get_current_user),
) -> AIRewriteResponse:
    """AI rewrite content (shorten/expand/improve)."""
    content = payload.content
    mode = payload.mode

    if mode not in ("shorten", "expand", "improve"):
        raise HTTPException(
            status_code=400, detail="Mode must be shorten, expand, or improve"
        )

    if mode == "shorten":
        sentences = content.split(". ")
        if len(sentences) > 2:
            rewritten = ". ".join(sentences[: len(sentences) // 2 + 1])
            if not rewritten.endswith("."):
                rewritten += "."
        else:
            rewritten = content
    elif mode == "expand":
        rewritten = (
            content
            + "\n\nAdditionally, this approach ensures comprehensive coverage of "
            "all stated requirements while maintaining alignment with the "
            "evaluation criteria."
        )
    else:  # improve
        rewritten = content.replace("  ", " ").strip()
        if not rewritten.endswith("."):
            rewritten += "."

    return AIRewriteResponse(
        original_length=len(content),
        rewritten=rewritten,
        rewritten_length=len(rewritten),
        mode=mode,
    )
