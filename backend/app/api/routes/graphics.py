"""
RFP Sniper - Proposal Graphics Routes
=====================================
API endpoints for proposal graphics requests.
"""

from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.api.deps import get_current_user
from app.services.auth_service import UserAuth
from app.models.graphics import ProposalGraphicRequest, GraphicsRequestStatus
from app.models.proposal import Proposal
from app.services.audit_service import log_audit_event
from app.services.graphics_generator import generate_graphic, TEMPLATE_TYPES

router = APIRouter(prefix="/graphics", tags=["Proposal Graphics"])


class GraphicsRequestCreate(BaseModel):
    proposal_id: int
    title: str
    description: Optional[str] = None
    section_id: Optional[int] = None
    due_date: Optional[date] = None


class GraphicsRequestUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    section_id: Optional[int] = None
    due_date: Optional[date] = None
    status: Optional[GraphicsRequestStatus] = None
    asset_url: Optional[str] = None
    notes: Optional[str] = None


class GraphicsRequestResponse(BaseModel):
    id: int
    proposal_id: int
    section_id: Optional[int]
    user_id: int
    title: str
    description: Optional[str]
    status: GraphicsRequestStatus
    due_date: Optional[date]
    asset_url: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


@router.get("", response_model=List[GraphicsRequestResponse])
async def list_requests(
    proposal_id: Optional[int] = Query(None),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[GraphicsRequestResponse]:
    query = select(ProposalGraphicRequest).where(
        ProposalGraphicRequest.user_id == current_user.id
    )
    if proposal_id is not None:
        query = query.where(ProposalGraphicRequest.proposal_id == proposal_id)
    result = await session.execute(query.order_by(ProposalGraphicRequest.created_at.desc()))
    items = result.scalars().all()
    return [GraphicsRequestResponse.model_validate(item) for item in items]


@router.post("", response_model=GraphicsRequestResponse)
async def create_request(
    payload: GraphicsRequestCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> GraphicsRequestResponse:
    proposal_result = await session.execute(
        select(Proposal).where(
            Proposal.id == payload.proposal_id,
            Proposal.user_id == current_user.id,
        )
    )
    if not proposal_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Proposal not found")

    request = ProposalGraphicRequest(
        proposal_id=payload.proposal_id,
        user_id=current_user.id,
        section_id=payload.section_id,
        title=payload.title,
        description=payload.description,
        due_date=payload.due_date,
    )
    session.add(request)
    await session.flush()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="proposal_graphics",
        entity_id=request.id,
        action="graphics.request_created",
        metadata={"proposal_id": payload.proposal_id},
    )
    await session.commit()
    await session.refresh(request)

    return GraphicsRequestResponse.model_validate(request)


@router.patch("/{request_id}", response_model=GraphicsRequestResponse)
async def update_request(
    request_id: int,
    payload: GraphicsRequestUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> GraphicsRequestResponse:
    result = await session.execute(
        select(ProposalGraphicRequest).where(
            ProposalGraphicRequest.id == request_id,
            ProposalGraphicRequest.user_id == current_user.id,
        )
    )
    request = result.scalar_one_or_none()
    if not request:
        raise HTTPException(status_code=404, detail="Graphics request not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(request, key, value)
    request.updated_at = datetime.utcnow()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="proposal_graphics",
        entity_id=request.id,
        action="graphics.request_updated",
        metadata={"updated_fields": list(update_data.keys())},
    )
    await session.commit()
    await session.refresh(request)

    return GraphicsRequestResponse.model_validate(request)


@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_request(
    request_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    result = await session.execute(
        select(ProposalGraphicRequest).where(
            ProposalGraphicRequest.id == request_id,
            ProposalGraphicRequest.user_id == current_user.id,
        )
    )
    request = result.scalar_one_or_none()
    if not request:
        raise HTTPException(status_code=404, detail="Graphics request not found")

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="proposal_graphics",
        entity_id=request.id,
        action="graphics.request_deleted",
    )

    await session.delete(request)
    await session.commit()


# ---------------------------------------------------------------------------
# AI Graphics Generation
# ---------------------------------------------------------------------------

class GraphicGeneratePayload(BaseModel):
    content: str
    template_type: str
    title: Optional[str] = None


class GraphicGenerateResponse(BaseModel):
    mermaid_code: str
    template_type: str
    title: str
    error: Optional[str] = None


class TemplateInfo(BaseModel):
    type: str
    label: str


@router.get("/templates", response_model=List[TemplateInfo])
async def list_templates(
    current_user: UserAuth = Depends(get_current_user),
) -> List[TemplateInfo]:
    """List available graphic template types."""
    return [
        TemplateInfo(type=t, label=t.replace("_", " ").title())
        for t in TEMPLATE_TYPES
    ]


@router.post("/generate", response_model=GraphicGenerateResponse)
async def generate_graphic_endpoint(
    payload: GraphicGeneratePayload,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> GraphicGenerateResponse:
    """Generate a Mermaid diagram from content using AI."""
    result = await generate_graphic(
        content=payload.content,
        template_type=payload.template_type,
        title=payload.title,
    )

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="proposal_graphics",
        entity_id=0,
        action="graphics.generated",
        metadata={"template_type": payload.template_type},
    )
    await session.commit()

    return GraphicGenerateResponse(**result)


@router.post("/{request_id}/asset", response_model=GraphicsRequestResponse)
async def store_graphic_asset(
    request_id: int,
    asset_url: str = Query(...),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> GraphicsRequestResponse:
    """Store a generated graphic asset URL on an existing request."""
    result = await session.execute(
        select(ProposalGraphicRequest).where(
            ProposalGraphicRequest.id == request_id,
            ProposalGraphicRequest.user_id == current_user.id,
        )
    )
    request = result.scalar_one_or_none()
    if not request:
        raise HTTPException(status_code=404, detail="Graphics request not found")

    request.asset_url = asset_url
    request.status = GraphicsRequestStatus.DELIVERED
    request.updated_at = datetime.utcnow()
    session.add(request)
    await session.commit()
    await session.refresh(request)
    return GraphicsRequestResponse.model_validate(request)
