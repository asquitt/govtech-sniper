"""
Bid Decision Routes
====================
AI-powered and human bid/no-bid scoring endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user_optional
from app.database import get_session
from app.models.capture import (
    BidScorecard,
    BidScorecardRecommendation,
    CapturePlan,
    ScorerType,
)
from app.models.rfp import RFP
from app.models.user import UserProfile
from app.services.auth_service import UserAuth

router = APIRouter()


class HumanVoteRequest(BaseModel):
    criteria_scores: list[dict]
    overall_score: float
    recommendation: BidScorecardRecommendation
    reasoning: str | None = None


class ScorecardResponse(BaseModel):
    id: int
    rfp_id: int
    user_id: int
    criteria_scores: list[dict]
    overall_score: float | None
    recommendation: str | None
    confidence: float | None
    reasoning: str | None
    scorer_type: str
    scorer_id: int | None
    created_at: str

    model_config = {"from_attributes": True}


@router.post("/scorecards/{rfp_id}/ai-evaluate")
async def ai_evaluate_bid(
    rfp_id: int = Path(..., description="RFP ID"),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Run AI bid/no-bid evaluation for an RFP."""
    from app.services.bid_decision_service import BidDecisionService

    result = await session.execute(select(RFP).where(RFP.id == rfp_id))
    rfp = result.scalar_one_or_none()
    if not rfp:
        raise HTTPException(status_code=404, detail=f"RFP {rfp_id} not found")

    profile_result = await session.execute(
        select(UserProfile).where(UserProfile.user_id == rfp.user_id)
    )
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=400, detail="User profile required for bid evaluation")

    service = BidDecisionService()
    scorecard = await service.evaluate(rfp, profile, user_id=rfp.user_id)
    session.add(scorecard)

    # Update CapturePlan win_probability if it exists
    plan_result = await session.execute(select(CapturePlan).where(CapturePlan.rfp_id == rfp_id))
    plan = plan_result.scalar_one_or_none()
    if plan:
        plan.win_probability = service.compute_win_probability(scorecard)

    await session.commit()
    await session.refresh(scorecard)

    return {
        "id": scorecard.id,
        "rfp_id": scorecard.rfp_id,
        "overall_score": scorecard.overall_score,
        "recommendation": scorecard.recommendation.value if scorecard.recommendation else None,
        "confidence": scorecard.confidence,
        "criteria_scores": scorecard.criteria_scores,
        "reasoning": scorecard.reasoning,
        "win_probability": plan.win_probability if plan else None,
    }


@router.post("/scorecards/{rfp_id}/vote")
async def submit_human_vote(
    vote: HumanVoteRequest,
    rfp_id: int = Path(..., description="RFP ID"),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Submit a human team member's bid/no-bid vote."""
    result = await session.execute(select(RFP).where(RFP.id == rfp_id))
    rfp = result.scalar_one_or_none()
    if not rfp:
        raise HTTPException(status_code=404, detail=f"RFP {rfp_id} not found")

    scorer_id = current_user.user_id if current_user else None

    scorecard = BidScorecard(
        rfp_id=rfp_id,
        user_id=rfp.user_id,
        criteria_scores=vote.criteria_scores,
        overall_score=vote.overall_score,
        recommendation=vote.recommendation,
        confidence=1.0,
        reasoning=vote.reasoning,
        scorer_type=ScorerType.HUMAN,
        scorer_id=scorer_id,
    )
    session.add(scorecard)
    await session.commit()
    await session.refresh(scorecard)

    return {
        "id": scorecard.id,
        "rfp_id": scorecard.rfp_id,
        "overall_score": scorecard.overall_score,
        "recommendation": scorecard.recommendation.value if scorecard.recommendation else None,
        "scorer_type": scorecard.scorer_type.value,
        "scorer_id": scorecard.scorer_id,
    }


@router.get("/scorecards/{rfp_id}")
async def list_scorecards(
    rfp_id: int = Path(..., description="RFP ID"),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    """List all scorecards (AI + human) for an RFP."""
    result = await session.execute(
        select(BidScorecard)
        .where(BidScorecard.rfp_id == rfp_id)
        .order_by(BidScorecard.created_at.desc())
    )
    scorecards = result.scalars().all()

    return [
        {
            "id": sc.id,
            "rfp_id": sc.rfp_id,
            "overall_score": sc.overall_score,
            "recommendation": sc.recommendation.value if sc.recommendation else None,
            "confidence": sc.confidence,
            "reasoning": sc.reasoning,
            "scorer_type": sc.scorer_type.value,
            "scorer_id": sc.scorer_id,
            "criteria_scores": sc.criteria_scores,
            "created_at": sc.created_at.isoformat(),
        }
        for sc in scorecards
    ]


@router.get("/scorecards/{rfp_id}/summary")
async def get_bid_summary(
    rfp_id: int = Path(..., description="RFP ID"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get aggregated bid decision summary with vote counts."""
    result = await session.execute(select(BidScorecard).where(BidScorecard.rfp_id == rfp_id))
    scorecards = result.scalars().all()

    if not scorecards:
        return {
            "rfp_id": rfp_id,
            "total_votes": 0,
            "ai_score": None,
            "human_avg": None,
            "overall_recommendation": None,
            "bid_count": 0,
            "no_bid_count": 0,
            "conditional_count": 0,
        }

    ai_cards = [sc for sc in scorecards if sc.scorer_type == ScorerType.AI]
    human_cards = [sc for sc in scorecards if sc.scorer_type == ScorerType.HUMAN]

    ai_score = ai_cards[-1].overall_score if ai_cards else None
    human_avg = None
    if human_cards:
        scores = [sc.overall_score for sc in human_cards if sc.overall_score is not None]
        human_avg = sum(scores) / len(scores) if scores else None

    bid_count = sum(1 for sc in scorecards if sc.recommendation == BidScorecardRecommendation.BID)
    no_bid_count = sum(
        1 for sc in scorecards if sc.recommendation == BidScorecardRecommendation.NO_BID
    )
    conditional_count = sum(
        1 for sc in scorecards if sc.recommendation == BidScorecardRecommendation.CONDITIONAL
    )

    # Determine overall recommendation by majority vote
    if bid_count > no_bid_count and bid_count > conditional_count:
        overall = "bid"
    elif no_bid_count > bid_count and no_bid_count > conditional_count:
        overall = "no_bid"
    elif conditional_count > 0:
        overall = "conditional"
    else:
        overall = "pending"

    return {
        "rfp_id": rfp_id,
        "total_votes": len(scorecards),
        "ai_score": ai_score,
        "human_avg": human_avg,
        "overall_recommendation": overall,
        "bid_count": bid_count,
        "no_bid_count": no_bid_count,
        "conditional_count": conditional_count,
    }
