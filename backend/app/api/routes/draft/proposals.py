"""
Draft Routes - Proposal CRUD
"""


from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user_optional, resolve_user_id
from app.database import get_session
from app.models.proposal import Proposal
from app.models.rfp import RFP
from app.schemas.proposal import ProposalCreate, ProposalRead
from app.services.auth_service import UserAuth

router = APIRouter()


@router.get("/proposals", response_model=list[ProposalRead])
async def list_proposals(
    user_id: int | None = Query(None, description="User ID (optional if authenticated)"),
    rfp_id: int | None = Query(None, description="Filter by RFP ID"),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> list[ProposalRead]:
    """
    List proposals for a user.
    """
    resolved_user_id = resolve_user_id(user_id, current_user)
    query = select(Proposal).where(Proposal.user_id == resolved_user_id)
    if rfp_id is not None:
        query = query.where(Proposal.rfp_id == rfp_id)

    result = await session.execute(query.order_by(Proposal.created_at.desc()))
    proposals = result.scalars().all()
    return [ProposalRead.from_orm_with_completion(p) for p in proposals]


@router.get("/proposals/{proposal_id}", response_model=ProposalRead)
async def get_proposal(
    proposal_id: int,
    session: AsyncSession = Depends(get_session),
) -> ProposalRead:
    """
    Get a proposal by id.
    """
    result = await session.execute(select(Proposal).where(Proposal.id == proposal_id))
    proposal = result.scalar_one_or_none()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    return ProposalRead.from_orm_with_completion(proposal)


@router.post("/proposals", response_model=ProposalRead)
async def create_proposal(
    proposal: ProposalCreate,
    user_id: int | None = Query(None, description="User ID (optional if authenticated)"),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> ProposalRead:
    """
    Create a new proposal for an RFP.

    This initializes the proposal structure. Use the sections
    endpoints to add content.
    """
    # Verify RFP exists
    result = await session.execute(select(RFP).where(RFP.id == proposal.rfp_id))
    rfp = result.scalar_one_or_none()

    if not rfp:
        raise HTTPException(status_code=404, detail=f"RFP {proposal.rfp_id} not found")

    resolved_user_id = resolve_user_id(user_id, current_user)

    # Create proposal
    new_proposal = Proposal(
        user_id=resolved_user_id,
        rfp_id=proposal.rfp_id,
        title=proposal.title,
    )
    session.add(new_proposal)
    await session.commit()
    await session.refresh(new_proposal)

    return ProposalRead.from_orm_with_completion(new_proposal)
