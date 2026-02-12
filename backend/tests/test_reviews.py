"""
RFP Sniper - Reviews Tests
==========================
Integration coverage for review scheduling, checklist, comments, and completion.
"""

import pytest
from httpx import AsyncClient

from app.models.proposal import Proposal


class TestReviews:
    @pytest.mark.asyncio
    async def test_review_dashboard_and_completion_flow(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
    ):
        schedule = await client.post(
            f"/api/v1/reviews/proposals/{test_proposal.id}/reviews",
            headers=auth_headers,
            json={"review_type": "red"},
        )
        assert schedule.status_code == 201
        review = schedule.json()
        review_id = review["id"]

        checklist = await client.post(
            f"/api/v1/reviews/{review_id}/checklist",
            headers=auth_headers,
            json={"review_type": "red"},
        )
        assert checklist.status_code == 201
        assert len(checklist.json()) > 0

        comment = await client.post(
            f"/api/v1/reviews/{review_id}/comments",
            headers=auth_headers,
            json={
                "comment_text": "Clarify the transition plan narrative.",
                "severity": "major",
            },
        )
        assert comment.status_code == 201
        assert comment.json()["status"] == "open"

        dashboard = await client.get("/api/v1/reviews/dashboard", headers=auth_headers)
        assert dashboard.status_code == 200
        assert any(item["review_id"] == review_id for item in dashboard.json())

        scoring = await client.get(
            f"/api/v1/reviews/{review_id}/scoring-summary",
            headers=auth_headers,
        )
        assert scoring.status_code == 200
        scoring_payload = scoring.json()
        assert scoring_payload["review_id"] == review_id
        assert "major" in scoring_payload["comments_by_severity"]

        complete = await client.patch(
            f"/api/v1/reviews/{review_id}/complete",
            headers=auth_headers,
            json={"overall_score": 86, "summary": "Ready for red-team closeout"},
        )
        assert complete.status_code == 200
        assert complete.json()["status"] == "completed"
