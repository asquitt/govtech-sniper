"""
Integration tests for reviews.py — /reviews/ color team reviews, assignments, comments, checklists
"""

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.proposal import Proposal
from app.models.review import ProposalReview, ReviewType
from app.models.rfp import RFP
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password


async def _create_second_user(db_session: AsyncSession) -> tuple[User, dict]:
    user2 = User(
        email="other@example.com",
        hashed_password=hash_password("OtherPass123!"),
        full_name="Other User",
        company_name="Other Co",
        tier="professional",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user2)
    await db_session.commit()
    await db_session.refresh(user2)
    tokens = create_token_pair(user2.id, user2.email, user2.tier)
    return user2, {"Authorization": f"Bearer {tokens.access_token}"}


class TestReviewDashboard:
    """GET /api/v1/reviews/dashboard"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/reviews/dashboard")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_dashboard(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.get("/api/v1/reviews/dashboard", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_dashboard_with_review(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
        test_proposal: Proposal,
    ):
        review = ProposalReview(
            proposal_id=test_proposal.id,
            review_type=ReviewType.PINK,
        )
        db_session.add(review)
        await db_session.commit()

        response = await client.get("/api/v1/reviews/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["review_type"] == "pink"


class TestScheduleReview:
    """POST /api/v1/reviews/proposals/{proposal_id}/reviews"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/reviews/proposals/1/reviews", json={"review_type": "pink"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_schedule_review(
        self, client: AsyncClient, auth_headers: dict, test_proposal: Proposal
    ):
        response = await client.post(
            f"/api/v1/reviews/proposals/{test_proposal.id}/reviews",
            headers=auth_headers,
            json={
                "review_type": "pink",
                "scheduled_date": (datetime.utcnow() + timedelta(days=3)).isoformat(),
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["review_type"] == "pink"
        assert data["status"] == "scheduled"


class TestListReviews:
    """GET /api/v1/reviews/proposals/{proposal_id}/reviews"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/reviews/proposals/1/reviews")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_reviews(
        self, client: AsyncClient, auth_headers: dict, test_proposal: Proposal
    ):
        await client.post(
            f"/api/v1/reviews/proposals/{test_proposal.id}/reviews",
            headers=auth_headers,
            json={"review_type": "pink"},
        )
        response = await client.get(
            f"/api/v1/reviews/proposals/{test_proposal.id}/reviews",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert len(response.json()) == 1


class TestAssignReviewer:
    """POST /api/v1/reviews/{review_id}/assign"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/reviews/1/assign", json={"reviewer_user_id": 1})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_assign_reviewer(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
        test_proposal: Proposal,
    ):
        create_response = await client.post(
            f"/api/v1/reviews/proposals/{test_proposal.id}/reviews",
            headers=auth_headers,
            json={"review_type": "red"},
        )
        review_id = create_response.json()["id"]

        response = await client.post(
            f"/api/v1/reviews/{review_id}/assign",
            headers=auth_headers,
            json={"reviewer_user_id": test_user.id},
        )
        assert response.status_code == 201
        assert response.json()["reviewer_user_id"] == test_user.id

    @pytest.mark.asyncio
    async def test_assign_review_not_found(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.post(
            "/api/v1/reviews/99999/assign",
            headers=auth_headers,
            json={"reviewer_user_id": test_user.id},
        )
        assert response.status_code == 404


class TestReviewComments:
    """POST/GET /api/v1/reviews/{review_id}/comments"""

    @pytest.mark.asyncio
    async def test_add_comment_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/reviews/1/comments",
            json={"comment_text": "Test", "severity": "minor"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_add_and_list_comments(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
    ):
        create_response = await client.post(
            f"/api/v1/reviews/proposals/{test_proposal.id}/reviews",
            headers=auth_headers,
            json={"review_type": "pink"},
        )
        review_id = create_response.json()["id"]

        add_response = await client.post(
            f"/api/v1/reviews/{review_id}/comments",
            headers=auth_headers,
            json={"comment_text": "Section needs work", "severity": "major"},
        )
        assert add_response.status_code == 201
        assert add_response.json()["severity"] == "major"

        list_response = await client.get(
            f"/api/v1/reviews/{review_id}/comments", headers=auth_headers
        )
        assert list_response.status_code == 200
        assert len(list_response.json()) == 1

    @pytest.mark.asyncio
    async def test_comment_review_not_found(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.post(
            "/api/v1/reviews/99999/comments",
            headers=auth_headers,
            json={"comment_text": "test", "severity": "minor"},
        )
        assert response.status_code == 404


class TestUpdateComment:
    """PATCH /api/v1/reviews/{review_id}/comments/{comment_id}"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.patch("/api/v1/reviews/1/comments/1", json={"status": "assigned"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_comment_status(
        self, client: AsyncClient, auth_headers: dict, test_proposal: Proposal
    ):
        create_response = await client.post(
            f"/api/v1/reviews/proposals/{test_proposal.id}/reviews",
            headers=auth_headers,
            json={"review_type": "pink"},
        )
        review_id = create_response.json()["id"]

        comment_response = await client.post(
            f"/api/v1/reviews/{review_id}/comments",
            headers=auth_headers,
            json={"comment_text": "Fix this", "severity": "critical"},
        )
        comment_id = comment_response.json()["id"]

        response = await client.patch(
            f"/api/v1/reviews/{review_id}/comments/{comment_id}",
            headers=auth_headers,
            json={"status": "addressed", "resolution_note": "Fixed in v2"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "addressed"
        assert response.json()["resolution_note"] == "Fixed in v2"

    @pytest.mark.asyncio
    async def test_update_comment_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_proposal: Proposal,
    ):
        review = ProposalReview(proposal_id=test_proposal.id, review_type=ReviewType.PINK)
        db_session.add(review)
        await db_session.commit()
        await db_session.refresh(review)

        response = await client.patch(
            f"/api/v1/reviews/{review.id}/comments/99999",
            headers=auth_headers,
            json={"status": "closed"},
        )
        assert response.status_code == 404


class TestScoringSummary:
    """GET /api/v1/reviews/{review_id}/scoring-summary"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/reviews/1/scoring-summary")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_scoring_summary(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_proposal: Proposal,
    ):
        review = ProposalReview(proposal_id=test_proposal.id, review_type=ReviewType.RED)
        db_session.add(review)
        await db_session.commit()
        await db_session.refresh(review)

        response = await client.get(
            f"/api/v1/reviews/{review.id}/scoring-summary", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["review_type"] == "red"
        assert "checklist_pass_rate" in data
        assert "total_comments" in data

    @pytest.mark.asyncio
    async def test_scoring_review_not_found(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.get("/api/v1/reviews/99999/scoring-summary", headers=auth_headers)
        assert response.status_code == 404


class TestReviewPacket:
    """GET /api/v1/reviews/{review_id}/packet"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/reviews/1/packet")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_packet(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
        test_proposal: Proposal,
    ):
        review = ProposalReview(proposal_id=test_proposal.id, review_type=ReviewType.GOLD)
        db_session.add(review)
        await db_session.commit()
        await db_session.refresh(review)

        response = await client.get(f"/api/v1/reviews/{review.id}/packet", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["review_type"] == "gold"
        assert "checklist_summary" in data
        assert "risk_summary" in data
        assert "action_queue" in data
        assert "recommended_exit_criteria" in data

    @pytest.mark.asyncio
    async def test_packet_idor(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        user2, _ = await _create_second_user(db_session)
        other_rfp = RFP(
            user_id=user2.id,
            title="Other RFP",
            solicitation_number="OTHER-001",
            notice_id="other-notice",
            agency="Other Agency",
            rfp_type="solicitation",
            status="new",
        )
        db_session.add(other_rfp)
        await db_session.flush()
        other_proposal = Proposal(
            user_id=user2.id, rfp_id=other_rfp.id, title="Other", status="draft"
        )
        db_session.add(other_proposal)
        await db_session.flush()

        review = ProposalReview(proposal_id=other_proposal.id, review_type=ReviewType.PINK)
        db_session.add(review)
        await db_session.commit()
        await db_session.refresh(review)

        response = await client.get(f"/api/v1/reviews/{review.id}/packet", headers=auth_headers)
        assert response.status_code == 404


class TestChecklist:
    """POST/GET/PATCH /api/v1/reviews/{review_id}/checklist"""

    @pytest.mark.asyncio
    async def test_create_checklist_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/reviews/1/checklist", json={"review_type": "pink"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_checklist_from_template(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_proposal: Proposal,
    ):
        review = ProposalReview(proposal_id=test_proposal.id, review_type=ReviewType.PINK)
        db_session.add(review)
        await db_session.commit()
        await db_session.refresh(review)

        response = await client.post(
            f"/api/v1/reviews/{review.id}/checklist",
            headers=auth_headers,
            json={"review_type": "pink"},
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data) > 0
        assert all("category" in item and "item_text" in item for item in data)

    @pytest.mark.asyncio
    async def test_list_checklist(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_proposal: Proposal,
    ):
        review = ProposalReview(proposal_id=test_proposal.id, review_type=ReviewType.RED)
        db_session.add(review)
        await db_session.commit()
        await db_session.refresh(review)

        # Create items
        await client.post(
            f"/api/v1/reviews/{review.id}/checklist",
            headers=auth_headers,
            json={"review_type": "red"},
        )

        response = await client.get(f"/api/v1/reviews/{review.id}/checklist", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) > 0

    @pytest.mark.asyncio
    async def test_update_checklist_item(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_proposal: Proposal,
    ):
        review = ProposalReview(proposal_id=test_proposal.id, review_type=ReviewType.PINK)
        db_session.add(review)
        await db_session.commit()
        await db_session.refresh(review)

        create_response = await client.post(
            f"/api/v1/reviews/{review.id}/checklist",
            headers=auth_headers,
            json={"review_type": "pink"},
        )
        item_id = create_response.json()[0]["id"]

        response = await client.patch(
            f"/api/v1/reviews/{review.id}/checklist/{item_id}",
            headers=auth_headers,
            json={"status": "pass", "reviewer_note": "Looks good"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "pass"
        assert response.json()["reviewer_note"] == "Looks good"


class TestCompleteReview:
    """PATCH /api/v1/reviews/{review_id}/complete"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.patch("/api/v1/reviews/1/complete", json={"overall_score": 85.0})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_complete_review(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_proposal: Proposal,
    ):
        review = ProposalReview(proposal_id=test_proposal.id, review_type=ReviewType.GOLD)
        db_session.add(review)
        await db_session.commit()
        await db_session.refresh(review)

        response = await client.patch(
            f"/api/v1/reviews/{review.id}/complete",
            headers=auth_headers,
            json={
                "overall_score": 92.5,
                "summary": "Strong proposal",
                "go_no_go_decision": "go",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["overall_score"] == 92.5
        assert data["go_no_go_decision"] == "go"

    @pytest.mark.asyncio
    async def test_complete_not_found(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.patch(
            "/api/v1/reviews/99999/complete",
            headers=auth_headers,
            json={"overall_score": 50.0},
        )
        assert response.status_code == 404
