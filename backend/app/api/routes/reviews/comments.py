"""
Reviews Routes - Comments
==========================
Add, list, update, and resolve review comments (including inline annotations).
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.proposal import Proposal
from app.models.review import (
    CommentSeverity,
    CommentStatus,
    ReviewComment,
)
from app.schemas.review import (
    CommentCreate,
    CommentRead,
    CommentUpdate,
)
from app.services.audit_service import log_audit_event
from app.services.auth_service import UserAuth

from .helpers import verify_review_ownership

router = APIRouter()


@router.post("/{review_id}/comments", response_model=CommentRead, status_code=201)
async def add_comment(
    review_id: int,
    payload: CommentCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CommentRead:
    """Add a review comment."""
    await verify_review_ownership(review_id, current_user.id, session)

    comment = ReviewComment(
        review_id=review_id,
        section_id=payload.section_id,
        reviewer_user_id=current_user.id,
        comment_text=payload.comment_text,
        severity=CommentSeverity(payload.severity),
        anchor_text=payload.anchor_text,
        anchor_offset_start=payload.anchor_offset_start,
        anchor_offset_end=payload.anchor_offset_end,
        is_inline=payload.is_inline,
        mentions=payload.mentions,
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


@router.get("/{review_id}/comments", response_model=list[CommentRead])
async def list_comments(
    review_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[CommentRead]:
    """List comments for a review."""
    await verify_review_ownership(review_id, current_user.id, session)

    result = await session.execute(
        select(ReviewComment)
        .where(ReviewComment.review_id == review_id)
        .order_by(ReviewComment.created_at.asc())
    )
    comments = result.scalars().all()
    return [CommentRead.model_validate(c) for c in comments]


@router.get("/sections/{section_id}/inline-comments", response_model=list[CommentRead])
async def list_inline_comments(
    section_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[CommentRead]:
    """List inline comments for a specific section (across all reviews)."""
    # Verify the user owns the proposal that contains this section
    from app.models.proposal import ProposalSection

    section_result = await session.execute(
        select(ProposalSection)
        .join(Proposal)
        .where(
            ProposalSection.id == section_id,
            Proposal.user_id == current_user.id,
        )
    )
    if not section_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Section not found")

    result = await session.execute(
        select(ReviewComment)
        .where(
            ReviewComment.section_id == section_id,
            ReviewComment.is_inline == True,  # noqa: E712
        )
        .order_by(ReviewComment.anchor_offset_start.asc())
    )
    return [CommentRead.model_validate(c) for c in result.scalars().all()]


@router.patch("/{review_id}/comments/{comment_id}", response_model=CommentRead)
async def update_comment(
    review_id: int,
    comment_id: int,
    payload: CommentUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CommentRead:
    """Update a comment status through the resolution workflow.

    Transitions: open->assigned, assigned->addressed, addressed->verified/closed,
    any->rejected.
    """
    await verify_review_ownership(review_id, current_user.id, session)
    result = await session.execute(
        select(ReviewComment).where(
            ReviewComment.id == comment_id,
            ReviewComment.review_id == review_id,
        )
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(404, "Comment not found")

    if payload.assigned_to_user_id is not None:
        comment.assigned_to_user_id = payload.assigned_to_user_id
        if comment.status == CommentStatus.OPEN:
            comment.status = CommentStatus.ASSIGNED

    if payload.status is not None:
        new_status = CommentStatus(payload.status)
        if new_status == CommentStatus.ADDRESSED:
            comment.resolved_by_user_id = current_user.id
            comment.resolved_at = datetime.utcnow()
        elif new_status in (CommentStatus.VERIFIED, CommentStatus.CLOSED):
            comment.verified_by_user_id = current_user.id
            comment.verified_at = datetime.utcnow()
        comment.status = new_status

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
