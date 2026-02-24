"""
Reviews Routes - Shared Helpers
================================
Ownership verification and review packet utility functions.
"""

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.utils import get_or_404
from app.models.proposal import Proposal
from app.models.review import ProposalReview


async def verify_proposal_ownership(
    proposal_id: int,
    user_id: int,
    session: AsyncSession,
) -> Proposal:
    """Verify the user owns the proposal. Raises 404 if not found or not owned."""
    result = await session.execute(
        select(Proposal).where(
            Proposal.id == proposal_id,
            Proposal.user_id == user_id,
        )
    )
    proposal = result.scalar_one_or_none()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return proposal


async def verify_review_ownership(
    review_id: int,
    user_id: int,
    session: AsyncSession,
) -> ProposalReview:
    """Load a review and verify the user owns its parent proposal."""
    review = await get_or_404(session, ProposalReview, review_id, "Review not found")
    await verify_proposal_ownership(review.proposal_id, user_id, session)
    return review


def review_packet_action_recommendation(severity: str, status: str) -> str:
    if status in {"closed", "verified", "rejected"}:
        return "No immediate action required. Confirm closure evidence is retained in packet."
    if severity == "critical":
        return "Assign immediate owner and patch before next review gate."
    if severity == "major":
        return "Address in next draft cycle and verify fix with reviewer."
    if severity == "minor":
        return "Apply cleanup edits before final quality review."
    return "Consider if this improves discriminator strength; apply if low effort/high value."


def review_packet_exit_criteria(
    review_type: str,
    checklist_pass_rate: float,
    open_critical: int,
    open_major: int,
) -> list[str]:
    if review_type == "pink":
        return [
            f"Open critical findings at pink exit must be 0 (current: {open_critical}).",
            f"Checklist pass-rate target for pink is >= 75% (current: {checklist_pass_rate:.1f}%).",
            "Solution narrative gaps should be resolved before red-team scheduling.",
        ]
    if review_type == "red":
        return [
            f"Open critical findings at red exit must be 0 (current: {open_critical}).",
            f"Open major findings at red exit should be <= 2 (current: {open_major}).",
            f"Checklist pass-rate target for red is >= 85% (current: {checklist_pass_rate:.1f}%).",
        ]
    return [
        f"Open critical findings at gold exit must be 0 (current: {open_critical}).",
        f"Open major findings at gold exit must be 0 (current: {open_major}).",
        f"Checklist pass-rate target for gold is >= 95% (current: {checklist_pass_rate:.1f}%).",
        "Go/No-Go decision must be documented in review closeout.",
    ]
