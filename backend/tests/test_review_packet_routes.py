"""
Integration tests for reviews/packet.py — scoring summary and review packet generation.
"""

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.proposal import Proposal
from app.models.review import (
    ChecklistItemStatus,
    CommentSeverity,
    CommentStatus,
    ProposalReview,
    ReviewChecklistItem,
    ReviewComment,
    ReviewType,
)
from app.models.user import User


@pytest.fixture
async def review_with_data(
    db_session: AsyncSession, test_user: User, test_proposal: Proposal
) -> ProposalReview:
    review = ProposalReview(
        proposal_id=test_proposal.id,
        review_type=ReviewType.RED,
        overall_score=82.5,
    )
    db_session.add(review)
    await db_session.flush()

    # Checklist items
    for i, status in enumerate(
        [
            ChecklistItemStatus.PASS,
            ChecklistItemStatus.PASS,
            ChecklistItemStatus.FAIL,
            ChecklistItemStatus.NA,
        ]
    ):
        db_session.add(
            ReviewChecklistItem(
                review_id=review.id,
                category="Technical",
                item_text=f"Check item {i}",
                status=status,
                display_order=i,
            )
        )

    # Comments with different severities
    db_session.add(
        ReviewComment(
            review_id=review.id,
            reviewer_user_id=test_user.id,
            comment_text="Critical issue",
            severity=CommentSeverity.CRITICAL,
            status=CommentStatus.OPEN,
            created_at=datetime.utcnow() - timedelta(days=3),
        )
    )
    db_session.add(
        ReviewComment(
            review_id=review.id,
            reviewer_user_id=test_user.id,
            comment_text="Major concern",
            severity=CommentSeverity.MAJOR,
            status=CommentStatus.ASSIGNED,
            created_at=datetime.utcnow() - timedelta(days=1),
        )
    )
    db_session.add(
        ReviewComment(
            review_id=review.id,
            reviewer_user_id=test_user.id,
            comment_text="Resolved item",
            severity=CommentSeverity.MINOR,
            status=CommentStatus.VERIFIED,
            created_at=datetime.utcnow() - timedelta(days=5),
        )
    )

    await db_session.commit()
    await db_session.refresh(review)
    return review


class TestScoringSummary:
    """GET /api/v1/reviews/{review_id}/scoring-summary"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/reviews/1/scoring-summary")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_scoring_summary(
        self,
        client: AsyncClient,
        auth_headers: dict,
        review_with_data: ProposalReview,
        test_user: User,
    ):
        resp = await client.get(
            f"/api/v1/reviews/{review_with_data.id}/scoring-summary",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["review_id"] == review_with_data.id
        assert data["review_type"] == "red"
        assert data["average_score"] == 82.5
        # 2 pass out of 4 total (NA excluded from fail count)
        assert data["checklist_pass_rate"] == 50.0
        assert data["total_comments"] == 3
        # 1 verified out of 3
        assert data["resolved_comments"] == 1

    @pytest.mark.asyncio
    async def test_review_not_found(self, client: AsyncClient, auth_headers: dict, test_user: User):
        resp = await client.get(
            "/api/v1/reviews/99999/scoring-summary",
            headers=auth_headers,
        )
        assert resp.status_code == 404


class TestReviewPacket:
    """GET /api/v1/reviews/{review_id}/packet"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/reviews/1/packet")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_review_packet(
        self,
        client: AsyncClient,
        auth_headers: dict,
        review_with_data: ProposalReview,
        test_user: User,
    ):
        resp = await client.get(
            f"/api/v1/reviews/{review_with_data.id}/packet",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["review_id"] == review_with_data.id
        assert data["review_type"] == "red"
        assert data["review_status"] == "scheduled"

        # Checklist summary
        cl = data["checklist_summary"]
        assert cl["total_items"] == 4
        assert cl["pass_count"] == 2
        assert cl["fail_count"] == 1
        assert cl["na_count"] == 1

        # Risk summary
        risk = data["risk_summary"]
        assert risk["open_critical"] == 1
        assert risk["open_major"] == 1
        assert risk["unresolved_comments"] == 2
        assert risk["overall_risk_level"] == "high"

        # Action queue ranked by risk
        queue = data["action_queue"]
        assert len(queue) == 2  # 2 actionable (open + assigned)
        assert queue[0]["rank"] == 1
        assert queue[0]["severity"] == "critical"
        assert queue[1]["rank"] == 2

    @pytest.mark.asyncio
    async def test_packet_review_not_found(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        resp = await client.get(
            "/api/v1/reviews/99999/packet",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_packet_empty_review(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
        test_proposal: Proposal,
    ):
        """Packet for a review with no comments/checklist items."""
        review = ProposalReview(
            proposal_id=test_proposal.id,
            review_type=ReviewType.PINK,
            overall_score=90.0,
        )
        db_session.add(review)
        await db_session.commit()
        await db_session.refresh(review)

        resp = await client.get(
            f"/api/v1/reviews/{review.id}/packet",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["checklist_summary"]["total_items"] == 0
        assert data["risk_summary"]["overall_risk_level"] == "low"
        assert data["action_queue"] == []
