"""Teaming Board - Performance Ratings."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.capture import TeamingPerformanceRating
from app.schemas.teaming import PerformanceRatingCreate, PerformanceRatingRead
from app.services.auth_service import UserAuth

router = APIRouter()


@router.post("/ratings", response_model=PerformanceRatingRead, status_code=201)
async def create_rating(
    payload: PerformanceRatingCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PerformanceRatingRead:
    """Rate a teaming partner's performance."""
    rating = TeamingPerformanceRating(
        user_id=current_user.id,
        partner_id=payload.partner_id,
        rfp_id=payload.rfp_id,
        rating=payload.rating,
        responsiveness=payload.responsiveness,
        quality=payload.quality,
        timeliness=payload.timeliness,
        comment=payload.comment,
    )
    session.add(rating)
    await session.commit()
    await session.refresh(rating)
    return PerformanceRatingRead.model_validate(rating)


@router.get("/partners/{partner_id}/ratings", response_model=list[PerformanceRatingRead])
async def list_partner_ratings(
    partner_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[PerformanceRatingRead]:
    """List performance ratings for a partner."""
    result = await session.execute(
        select(TeamingPerformanceRating)
        .where(TeamingPerformanceRating.partner_id == partner_id)
        .order_by(TeamingPerformanceRating.created_at.desc())
    )
    return [PerformanceRatingRead.model_validate(r) for r in result.scalars().all()]
