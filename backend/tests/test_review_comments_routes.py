"""
Integration tests for reviews/comments.py — review comment CRUD and inline comments.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.proposal import Proposal, ProposalSection
from app.models.review import (
    CommentSeverity,
    CommentStatus,
    ProposalReview,
    ReviewComment,
    ReviewType,
)
from app.models.user import User


@pytest.fixture
async def review_with_proposal(
    db_session: AsyncSession, test_user: User, test_proposal: Proposal
) -> ProposalReview:
    review = ProposalReview(
        proposal_id=test_proposal.id,
        review_type=ReviewType.PINK,
        overall_score=75.0,
    )
    db_session.add(review)
    await db_session.commit()
    await db_session.refresh(review)
    return review


@pytest.fixture
async def section_for_review(db_session: AsyncSession, test_proposal: Proposal) -> ProposalSection:
    section = ProposalSection(
        proposal_id=test_proposal.id,
        title="Technical Approach",
        section_number="3.1",
        display_order=1,
    )
    db_session.add(section)
    await db_session.commit()
    await db_session.refresh(section)
    return section


class TestAddComment:
    """POST /api/v1/reviews/{review_id}/comments"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/reviews/1/comments", json={"comment_text": "x", "severity": "minor"}
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_add_comment(
        self,
        client: AsyncClient,
        auth_headers: dict,
        review_with_proposal: ProposalReview,
        test_user: User,
    ):
        resp = await client.post(
            f"/api/v1/reviews/{review_with_proposal.id}/comments",
            headers=auth_headers,
            json={"comment_text": "Needs citation", "severity": "major"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["comment_text"] == "Needs citation"
        assert data["severity"] == "major"
        assert data["status"] == "open"

    @pytest.mark.asyncio
    async def test_add_inline_comment(
        self,
        client: AsyncClient,
        auth_headers: dict,
        review_with_proposal: ProposalReview,
        section_for_review: ProposalSection,
        test_user: User,
    ):
        resp = await client.post(
            f"/api/v1/reviews/{review_with_proposal.id}/comments",
            headers=auth_headers,
            json={
                "comment_text": "Inline note",
                "severity": "suggestion",
                "section_id": section_for_review.id,
                "is_inline": True,
                "anchor_text": "some text",
                "anchor_offset_start": 10,
                "anchor_offset_end": 19,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["is_inline"] is True
        assert data["section_id"] == section_for_review.id

    @pytest.mark.asyncio
    async def test_add_comment_review_not_found(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        resp = await client.post(
            "/api/v1/reviews/99999/comments",
            headers=auth_headers,
            json={"comment_text": "Ghost", "severity": "minor"},
        )
        assert resp.status_code == 404


class TestListComments:
    """GET /api/v1/reviews/{review_id}/comments"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/reviews/1/comments")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_list(
        self,
        client: AsyncClient,
        auth_headers: dict,
        review_with_proposal: ProposalReview,
        test_user: User,
    ):
        resp = await client.get(
            f"/api/v1/reviews/{review_with_proposal.id}/comments",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_comments(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        review_with_proposal: ProposalReview,
        test_user: User,
    ):
        comment = ReviewComment(
            review_id=review_with_proposal.id,
            reviewer_user_id=test_user.id,
            comment_text="First comment",
            severity=CommentSeverity.MINOR,
        )
        db_session.add(comment)
        await db_session.commit()

        resp = await client.get(
            f"/api/v1/reviews/{review_with_proposal.id}/comments",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["comment_text"] == "First comment"


class TestListInlineComments:
    """GET /api/v1/reviews/sections/{section_id}/inline-comments"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/reviews/sections/1/inline-comments")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_section_not_found(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        resp = await client.get(
            "/api/v1/reviews/sections/99999/inline-comments",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_inline_comments_for_section(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        review_with_proposal: ProposalReview,
        section_for_review: ProposalSection,
        test_user: User,
    ):
        comment = ReviewComment(
            review_id=review_with_proposal.id,
            section_id=section_for_review.id,
            reviewer_user_id=test_user.id,
            comment_text="Inline annotation",
            severity=CommentSeverity.SUGGESTION,
            is_inline=True,
            anchor_text="some text",
            anchor_offset_start=0,
            anchor_offset_end=9,
        )
        db_session.add(comment)
        await db_session.commit()

        resp = await client.get(
            f"/api/v1/reviews/sections/{section_for_review.id}/inline-comments",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["is_inline"] is True


class TestUpdateComment:
    """PATCH /api/v1/reviews/{review_id}/comments/{comment_id}"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.patch("/api/v1/reviews/1/comments/1", json={})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_update_status(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        review_with_proposal: ProposalReview,
        test_user: User,
    ):
        comment = ReviewComment(
            review_id=review_with_proposal.id,
            reviewer_user_id=test_user.id,
            comment_text="Needs work",
            severity=CommentSeverity.MAJOR,
            status=CommentStatus.OPEN,
        )
        db_session.add(comment)
        await db_session.commit()
        await db_session.refresh(comment)

        resp = await client.patch(
            f"/api/v1/reviews/{review_with_proposal.id}/comments/{comment.id}",
            headers=auth_headers,
            json={"status": "addressed", "resolution_note": "Fixed the issue"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "addressed"
        assert data["resolution_note"] == "Fixed the issue"

    @pytest.mark.asyncio
    async def test_assign_comment(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        review_with_proposal: ProposalReview,
        test_user: User,
    ):
        comment = ReviewComment(
            review_id=review_with_proposal.id,
            reviewer_user_id=test_user.id,
            comment_text="Assign me",
            severity=CommentSeverity.MINOR,
            status=CommentStatus.OPEN,
        )
        db_session.add(comment)
        await db_session.commit()
        await db_session.refresh(comment)

        resp = await client.patch(
            f"/api/v1/reviews/{review_with_proposal.id}/comments/{comment.id}",
            headers=auth_headers,
            json={"assigned_to_user_id": test_user.id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["assigned_to_user_id"] == test_user.id
        assert data["status"] == "assigned"

    @pytest.mark.asyncio
    async def test_comment_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
        review_with_proposal: ProposalReview,
        test_user: User,
    ):
        resp = await client.patch(
            f"/api/v1/reviews/{review_with_proposal.id}/comments/99999",
            headers=auth_headers,
            json={"status": "closed"},
        )
        assert resp.status_code == 404
