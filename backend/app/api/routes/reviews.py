"""
RFP Sniper - Color Team Review Routes
=======================================
Schedule, assign, comment on, and complete color team reviews.
"""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func

from app.database import get_session
from app.api.deps import get_current_user
from app.services.auth_service import UserAuth
from app.models.review import (
    ProposalReview,
    ReviewAssignment,
    ReviewComment,
    ReviewType,
    ReviewStatus,
    AssignmentStatus,
    CommentSeverity,
    CommentStatus,
)
from app.schemas.review import (
    ReviewCreate,
    ReviewRead,
    ReviewComplete,
    AssignmentCreate,
    AssignmentRead,
    CommentCreate,
    CommentUpdate,
    CommentRead,
)
from app.services.audit_service import log_audit_event
from app.services.webhook_service import dispatch_webhook_event

router = APIRouter(prefix="/reviews", tags=["Reviews"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_review_or_404(
    review_id: int,
    session: AsyncSession,
) -> ProposalReview:
    review = await session.get(ProposalReview, review_id)
    if not review:
        raise HTTPException(404, "Review not found")
    return review


# ---------------------------------------------------------------------------
# Schedule / List reviews for a proposal
# ---------------------------------------------------------------------------

@router.post("/proposals/{proposal_id}/reviews", response_model=ReviewRead, status_code=201)
async def schedule_review(
    proposal_id: int,
    payload: ReviewCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ReviewRead:
    """Schedule a color team review (pink/red/gold) for a proposal."""
    review = ProposalReview(
        proposal_id=proposal_id,
        review_type=ReviewType(payload.review_type),
        scheduled_date=payload.scheduled_date,
    )
    session.add(review)
    await session.commit()
    await session.refresh(review)

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="proposal_review",
        entity_id=review.id,
        action="review.scheduled",
        metadata={"proposal_id": proposal_id, "review_type": payload.review_type},
    )
    await dispatch_webhook_event(
        session,
        user_id=current_user.id,
        event_type="review.scheduled",
        payload={"review_id": review.id, "proposal_id": proposal_id, "review_type": payload.review_type},
    )

    return ReviewRead.model_validate(review)


@router.get("/proposals/{proposal_id}/reviews", response_model=List[ReviewRead])
async def list_reviews(
    proposal_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[ReviewRead]:
    """List all reviews for a proposal."""
    result = await session.execute(
        select(ProposalReview)
        .where(ProposalReview.proposal_id == proposal_id)
        .order_by(ProposalReview.created_at.desc())
    )
    reviews = result.scalars().all()
    return [ReviewRead.model_validate(r) for r in reviews]


# ---------------------------------------------------------------------------
# Assign reviewers
# ---------------------------------------------------------------------------

@router.post("/{review_id}/assign", response_model=AssignmentRead, status_code=201)
async def assign_reviewer(
    review_id: int,
    payload: AssignmentCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AssignmentRead:
    """Assign a reviewer to a review."""
    await _get_review_or_404(review_id, session)

    assignment = ReviewAssignment(
        review_id=review_id,
        reviewer_user_id=payload.reviewer_user_id,
    )
    session.add(assignment)
    await session.commit()
    await session.refresh(assignment)

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="review_assignment",
        entity_id=assignment.id,
        action="review.reviewer_assigned",
        metadata={"review_id": review_id, "reviewer_user_id": payload.reviewer_user_id},
    )

    return AssignmentRead.model_validate(assignment)


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------

@router.post("/{review_id}/comments", response_model=CommentRead, status_code=201)
async def add_comment(
    review_id: int,
    payload: CommentCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CommentRead:
    """Add a review comment."""
    await _get_review_or_404(review_id, session)

    comment = ReviewComment(
        review_id=review_id,
        section_id=payload.section_id,
        reviewer_user_id=current_user.id,
        comment_text=payload.comment_text,
        severity=CommentSeverity(payload.severity),
    )
    session.add(comment)
    await session.commit()
    await session.refresh(comment)

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="review_comment",
        entity_id=comment.id,
        action="review.comment_added",
        metadata={"review_id": review_id, "severity": payload.severity},
    )

    return CommentRead.model_validate(comment)


@router.get("/{review_id}/comments", response_model=List[CommentRead])
async def list_comments(
    review_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[CommentRead]:
    """List comments for a review."""
    await _get_review_or_404(review_id, session)

    result = await session.execute(
        select(ReviewComment)
        .where(ReviewComment.review_id == review_id)
        .order_by(ReviewComment.created_at.asc())
    )
    comments = result.scalars().all()
    return [CommentRead.model_validate(c) for c in comments]


@router.patch("/{review_id}/comments/{comment_id}", response_model=CommentRead)
async def update_comment(
    review_id: int,
    comment_id: int,
    payload: CommentUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CommentRead:
    """Resolve, accept, or reject a review comment."""
    result = await session.execute(
        select(ReviewComment).where(
            ReviewComment.id == comment_id,
            ReviewComment.review_id == review_id,
        )
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(404, "Comment not found")

    if payload.status is not None:
        comment.status = CommentStatus(payload.status)
    if payload.resolution_note is not None:
        comment.resolution_note = payload.resolution_note

    session.add(comment)
    await session.commit()
    await session.refresh(comment)

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="review_comment",
        entity_id=comment.id,
        action="review.comment_updated",
        metadata={"review_id": review_id, "new_status": payload.status},
    )

    return CommentRead.model_validate(comment)


# ---------------------------------------------------------------------------
# Complete review
# ---------------------------------------------------------------------------

@router.patch("/{review_id}/complete", response_model=ReviewRead)
async def complete_review(
    review_id: int,
    payload: ReviewComplete,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ReviewRead:
    """Complete a review with an overall score."""
    review = await _get_review_or_404(review_id, session)

    review.status = ReviewStatus.COMPLETED
    review.completed_date = datetime.utcnow()
    review.overall_score = payload.overall_score
    if payload.summary is not None:
        review.summary = payload.summary
    review.updated_at = datetime.utcnow()

    session.add(review)
    await session.commit()
    await session.refresh(review)

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="proposal_review",
        entity_id=review.id,
        action="review.completed",
        metadata={"overall_score": payload.overall_score},
    )
    await dispatch_webhook_event(
        session,
        user_id=current_user.id,
        event_type="review.completed",
        payload={"review_id": review.id, "overall_score": payload.overall_score},
    )

    return ReviewRead.model_validate(review)
