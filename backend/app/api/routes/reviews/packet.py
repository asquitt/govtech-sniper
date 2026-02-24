"""
Reviews Routes - Scoring & Review Packet
==========================================
Scoring summary and risk-ranked review packet generation.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from app.api.deps import get_current_user
from app.api.utils import get_or_404
from app.database import get_session
from app.models.proposal import Proposal
from app.models.review import (
    ChecklistItemStatus,
    CommentSeverity,
    CommentStatus,
    ProposalReview,
    ReviewChecklistItem,
    ReviewComment,
    ReviewStatus,
    ReviewType,
)
from app.schemas.review import (
    ReviewPacketActionItem,
    ReviewPacketChecklistSummary,
    ReviewPacketRead,
    ReviewPacketRiskSummary,
    ScoringSummary,
)
from app.services.auth_service import UserAuth

from .helpers import (
    review_packet_action_recommendation,
    review_packet_exit_criteria,
    verify_review_ownership,
)

router = APIRouter()


@router.get("/{review_id}/scoring-summary", response_model=ScoringSummary)
async def get_scoring_summary(
    review_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ScoringSummary:
    """Aggregated scoring summary for a review."""
    review = await verify_review_ownership(review_id, current_user.id, session)

    # Checklist pass rate
    checklist_result = await session.execute(
        select(
            func.count(ReviewChecklistItem.id),
            func.count(ReviewChecklistItem.id).filter(
                ReviewChecklistItem.status == ChecklistItemStatus.PASS
            ),
        ).where(ReviewChecklistItem.review_id == review_id)
    )
    total_items, passed_items = checklist_result.one()
    checklist_pass_rate = (passed_items / total_items * 100) if total_items else 0.0

    # Comments by severity + resolution rate
    comments_result = await session.execute(
        select(ReviewComment.severity, ReviewComment.status).where(
            ReviewComment.review_id == review_id
        )
    )
    rows = comments_result.all()
    severity_counts: dict[str, int] = {}
    total_comments = 0
    resolved_comments = 0
    terminal_statuses = {CommentStatus.VERIFIED, CommentStatus.CLOSED, CommentStatus.REJECTED}
    for sev, status in rows:
        sev_val = sev.value if hasattr(sev, "value") else sev
        severity_counts[sev_val] = severity_counts.get(sev_val, 0) + 1
        total_comments += 1
        status_val = status.value if hasattr(status, "value") else status
        if status_val in {s.value for s in terminal_statuses}:
            resolved_comments += 1

    resolution_rate = (resolved_comments / total_comments * 100) if total_comments else 0.0

    review_type_val = (
        review.review_type.value
        if isinstance(review.review_type, ReviewType)
        else review.review_type
    )

    return ScoringSummary(
        review_id=review_id,
        review_type=review_type_val,
        average_score=review.overall_score,
        min_score=review.overall_score,
        max_score=review.overall_score,
        checklist_pass_rate=round(checklist_pass_rate, 1),
        comments_by_severity=severity_counts,
        resolution_rate=round(resolution_rate, 1),
        total_comments=total_comments,
        resolved_comments=resolved_comments,
    )


@router.get("/{review_id}/packet", response_model=ReviewPacketRead)
async def get_review_packet(
    review_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ReviewPacketRead:
    """Generate a review packet with a risk-ranked action queue."""
    review = await get_or_404(session, ProposalReview, review_id, "Review not found")

    proposal_result = await session.execute(
        select(Proposal).where(
            Proposal.id == review.proposal_id,
            Proposal.user_id == current_user.id,
        )
    )
    proposal = proposal_result.scalar_one_or_none()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    comments_result = await session.execute(
        select(ReviewComment)
        .where(ReviewComment.review_id == review_id)
        .order_by(ReviewComment.created_at.asc())
    )
    comments = comments_result.scalars().all()

    checklist_result = await session.execute(
        select(ReviewChecklistItem).where(ReviewChecklistItem.review_id == review_id)
    )
    checklist_items = checklist_result.scalars().all()

    checklist_status = [
        item.status.value if hasattr(item.status, "value") else str(item.status)
        for item in checklist_items
    ]
    total_items = len(checklist_status)
    pass_count = sum(1 for status in checklist_status if status == ChecklistItemStatus.PASS.value)
    fail_count = sum(1 for status in checklist_status if status == ChecklistItemStatus.FAIL.value)
    pending_count = sum(
        1 for status in checklist_status if status == ChecklistItemStatus.PENDING.value
    )
    na_count = sum(1 for status in checklist_status if status == ChecklistItemStatus.NA.value)
    pass_rate = round((pass_count / total_items * 100) if total_items else 0.0, 1)

    severity_weights = {"critical": 100.0, "major": 75.0, "minor": 45.0, "suggestion": 20.0}
    status_multipliers = {
        "open": 1.0,
        "assigned": 0.85,
        "addressed": 0.55,
        "verified": 0.25,
        "closed": 0.1,
        "rejected": 0.1,
    }
    actionable_statuses = {"open", "assigned", "addressed"}

    action_queue: list[ReviewPacketActionItem] = []
    unresolved_comments = 0
    open_critical = 0
    open_major = 0
    highest_risk = 0.0

    now = datetime.utcnow()
    for comment in comments:
        severity = (
            comment.severity.value if hasattr(comment.severity, "value") else str(comment.severity)
        )
        status = comment.status.value if hasattr(comment.status, "value") else str(comment.status)
        if status not in actionable_statuses:
            continue

        unresolved_comments += 1
        if severity == CommentSeverity.CRITICAL.value:
            open_critical += 1
        if severity == CommentSeverity.MAJOR.value:
            open_major += 1

        age_days = max((now - comment.created_at).days, 0)
        age_boost = min(age_days * 1.5, 20.0)
        risk_score = round(
            (severity_weights.get(severity, 30.0) * status_multipliers.get(status, 1.0))
            + age_boost,
            1,
        )
        highest_risk = max(highest_risk, risk_score)

        recommendation = review_packet_action_recommendation(severity=severity, status=status)
        action_queue.append(
            ReviewPacketActionItem(
                rank=0,  # populated after sorting
                comment_id=comment.id,  # type: ignore[arg-type]
                section_id=comment.section_id,
                severity=severity,
                status=status,
                risk_score=risk_score,
                age_days=age_days,
                assigned_to_user_id=comment.assigned_to_user_id,
                recommended_action=recommendation,
                rationale=(
                    f"{severity.title()} severity with {status.replace('_', ' ')} status "
                    f"and age {age_days}d."
                ),
            )
        )

    action_queue.sort(key=lambda item: (-item.risk_score, item.age_days, item.comment_id))
    for index, item in enumerate(action_queue, start=1):
        item.rank = index

    if open_critical > 0 or highest_risk >= 85:
        risk_level = "high"
    elif open_major > 0 or unresolved_comments > 0:
        risk_level = "medium"
    else:
        risk_level = "low"

    review_type_val = (
        review.review_type.value
        if isinstance(review.review_type, ReviewType)
        else review.review_type
    )
    review_status_val = (
        review.status.value if isinstance(review.status, ReviewStatus) else review.status
    )

    return ReviewPacketRead(
        review_id=review.id,  # type: ignore[arg-type]
        proposal_id=proposal.id,  # type: ignore[arg-type]
        proposal_title=proposal.title,
        review_type=review_type_val,
        review_status=review_status_val,
        generated_at=datetime.utcnow(),
        checklist_summary=ReviewPacketChecklistSummary(
            total_items=total_items,
            pass_count=pass_count,
            fail_count=fail_count,
            pending_count=pending_count,
            na_count=na_count,
            pass_rate=pass_rate,
        ),
        risk_summary=ReviewPacketRiskSummary(
            open_critical=open_critical,
            open_major=open_major,
            unresolved_comments=unresolved_comments,
            highest_risk_score=round(highest_risk, 1),
            overall_risk_level=risk_level,
        ),
        action_queue=action_queue,
        recommended_exit_criteria=review_packet_exit_criteria(
            review_type=review_type_val,
            checklist_pass_rate=pass_rate,
            open_critical=open_critical,
            open_major=open_major,
        ),
    )
