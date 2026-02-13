"""
RFP Sniper - Color Team Review Routes
=======================================
Schedule, assign, comment on, and complete color team reviews.
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
    ReviewAssignment,
    ReviewChecklistItem,
    ReviewComment,
    ReviewStatus,
    ReviewType,
)
from app.schemas.review import (
    AssignmentCreate,
    AssignmentRead,
    ChecklistCreateFromTemplate,
    ChecklistItemRead,
    ChecklistItemUpdate,
    CommentCreate,
    CommentRead,
    CommentUpdate,
    ReviewComplete,
    ReviewCreate,
    ReviewDashboardItem,
    ReviewRead,
    ScoringSummary,
)
from app.services.audit_service import log_audit_event
from app.services.auth_service import UserAuth
from app.services.review_checklist_templates import get_checklist_template
from app.services.webhook_service import dispatch_webhook_event

router = APIRouter(prefix="/reviews", tags=["Reviews"])


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


@router.get("/dashboard", response_model=list[ReviewDashboardItem])
async def review_dashboard(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ReviewDashboardItem]:
    """List all active reviews across proposals for the current user."""
    proposals_result = await session.execute(
        select(Proposal.id, Proposal.title).where(Proposal.user_id == current_user.id)
    )
    proposals = {row[0]: row[1] for row in proposals_result.all()}
    if not proposals:
        return []

    proposal_ids = list(proposals.keys())

    reviews_result = await session.execute(
        select(ProposalReview)
        .where(ProposalReview.proposal_id.in_(proposal_ids))
        .order_by(ProposalReview.created_at.desc())
    )
    reviews = reviews_result.scalars().all()

    items: list[ReviewDashboardItem] = []
    for review in reviews:
        comment_counts = await session.execute(
            select(
                func.count(ReviewComment.id),
                func.count(ReviewComment.id).filter(ReviewComment.status == CommentStatus.OPEN),
            ).where(ReviewComment.review_id == review.id)
        )
        total_comments, open_comments = comment_counts.one()

        assignment_counts = await session.execute(
            select(
                func.count(ReviewAssignment.id),
                func.count(ReviewAssignment.id).filter(ReviewAssignment.status == "completed"),
            ).where(ReviewAssignment.review_id == review.id)
        )
        total_assignments, completed_assignments = assignment_counts.one()

        items.append(
            ReviewDashboardItem(
                review_id=review.id,  # type: ignore[arg-type]
                proposal_id=review.proposal_id,
                proposal_title=proposals.get(review.proposal_id, ""),
                review_type=review.review_type.value
                if isinstance(review.review_type, ReviewType)
                else review.review_type,
                status=review.status.value
                if isinstance(review.status, ReviewStatus)
                else review.status,
                scheduled_date=review.scheduled_date,
                overall_score=review.overall_score,
                go_no_go_decision=review.go_no_go_decision,
                total_comments=total_comments or 0,
                open_comments=open_comments or 0,
                total_assignments=total_assignments or 0,
                completed_assignments=completed_assignments or 0,
            )
        )

    return items


# ---------------------------------------------------------------------------
# Schedule / List reviews for a proposal
# ---------------------------------------------------------------------------


@router.post(
    "/proposals/{proposal_id}/reviews",
    response_model=ReviewRead,
    status_code=201,
)
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
        metadata={
            "proposal_id": proposal_id,
            "review_type": payload.review_type,
        },
    )
    await dispatch_webhook_event(
        session,
        user_id=current_user.id,
        event_type="review.scheduled",
        payload={
            "review_id": review.id,
            "proposal_id": proposal_id,
            "review_type": payload.review_type,
        },
    )

    return ReviewRead.model_validate(review)


@router.get("/proposals/{proposal_id}/reviews", response_model=list[ReviewRead])
async def list_reviews(
    proposal_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ReviewRead]:
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
    await get_or_404(session, ProposalReview, review_id, "Review not found")

    assignment = ReviewAssignment(
        review_id=review_id,
        reviewer_user_id=payload.reviewer_user_id,
        due_date=payload.due_date,
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
        metadata={
            "review_id": review_id,
            "reviewer_user_id": payload.reviewer_user_id,
        },
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
    await get_or_404(session, ProposalReview, review_id, "Review not found")

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
    await get_or_404(session, ProposalReview, review_id, "Review not found")

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

    Transitions: open→assigned, assigned→addressed, addressed→verified/closed,
    any→rejected.
    """
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


# ---------------------------------------------------------------------------
# Scoring Summary
# ---------------------------------------------------------------------------


@router.get("/{review_id}/scoring-summary", response_model=ScoringSummary)
async def get_scoring_summary(
    review_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ScoringSummary:
    """Aggregated scoring summary for a review."""
    review = await get_or_404(session, ProposalReview, review_id, "Review not found")

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


# ---------------------------------------------------------------------------
# Checklists
# ---------------------------------------------------------------------------


@router.post(
    "/{review_id}/checklist",
    response_model=list[ChecklistItemRead],
    status_code=201,
)
async def create_checklist_from_template(
    review_id: int,
    payload: ChecklistCreateFromTemplate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ChecklistItemRead]:
    """Bulk-create checklist items from a review type template."""
    await get_or_404(session, ProposalReview, review_id, "Review not found")

    template = get_checklist_template(payload.review_type)
    if not template:
        raise HTTPException(400, f"No template for review type: {payload.review_type}")

    items: list[ReviewChecklistItem] = []
    for entry in template:
        item = ReviewChecklistItem(
            review_id=review_id,
            category=entry["category"],
            item_text=entry["item_text"],
            display_order=entry["display_order"],
        )
        session.add(item)
        items.append(item)

    await session.commit()
    for item in items:
        await session.refresh(item)

    return [ChecklistItemRead.model_validate(i) for i in items]


@router.get("/{review_id}/checklist", response_model=list[ChecklistItemRead])
async def list_checklist(
    review_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ChecklistItemRead]:
    """List checklist items for a review."""
    await get_or_404(session, ProposalReview, review_id, "Review not found")

    result = await session.execute(
        select(ReviewChecklistItem)
        .where(ReviewChecklistItem.review_id == review_id)
        .order_by(ReviewChecklistItem.display_order.asc())
    )
    return [ChecklistItemRead.model_validate(i) for i in result.scalars().all()]


@router.patch("/{review_id}/checklist/{item_id}", response_model=ChecklistItemRead)
async def update_checklist_item(
    review_id: int,
    item_id: int,
    payload: ChecklistItemUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ChecklistItemRead:
    """Update a checklist item status or note."""
    result = await session.execute(
        select(ReviewChecklistItem).where(
            ReviewChecklistItem.id == item_id,
            ReviewChecklistItem.review_id == review_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Checklist item not found")

    if payload.status is not None:
        item.status = ChecklistItemStatus(payload.status)
    if payload.reviewer_note is not None:
        item.reviewer_note = payload.reviewer_note

    session.add(item)
    await session.commit()
    await session.refresh(item)

    return ChecklistItemRead.model_validate(item)


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
    review = await get_or_404(session, ProposalReview, review_id, "Review not found")

    review.status = ReviewStatus.COMPLETED
    review.completed_date = datetime.utcnow()
    review.overall_score = payload.overall_score
    if payload.summary is not None:
        review.summary = payload.summary
    if payload.go_no_go_decision is not None:
        review.go_no_go_decision = payload.go_no_go_decision
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
        payload={
            "review_id": review.id,
            "overall_score": payload.overall_score,
        },
    )

    return ReviewRead.model_validate(review)
