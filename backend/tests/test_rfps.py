"""
RFP Sniper - RFP Management Tests
=================================
Tests for RFP CRUD operations.
"""

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.opportunity_snapshot import SAMOpportunitySnapshot
from app.models.proposal import Proposal, ProposalSection
from app.models.rfp import RFP
from app.models.user import User


class TestRFPList:
    """Tests for RFP listing."""

    @pytest.mark.asyncio
    async def test_list_rfps_empty(self, client: AsyncClient, test_user: User):
        """Test listing RFPs when none exist."""
        response = await client.get(
            "/api/v1/rfps",
            params={"user_id": test_user.id},
        )
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_rfps_with_data(self, client: AsyncClient, test_user: User, test_rfp: RFP):
        """Test listing RFPs with existing data."""
        response = await client.get(
            "/api/v1/rfps",
            params={"user_id": test_user.id},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == test_rfp.id
        assert data[0]["title"] == test_rfp.title
        assert data[0]["classification"] == "internal"
        assert "recommendation_score" in data[0]

    @pytest.mark.asyncio
    async def test_list_rfps_pagination(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User
    ):
        """Test RFP listing pagination."""
        # Create multiple RFPs
        for i in range(15):
            rfp = RFP(
                user_id=test_user.id,
                title=f"Test RFP {i}",
                solicitation_number=f"SOL-{i:04d}",
                notice_id=f"notice-{i}",
                agency="Test Agency",
                rfp_type="solicitation",
                status="new",
                posted_date=datetime.utcnow(),
            )
            db_session.add(rfp)
        await db_session.commit()

        # Test first page
        response = await client.get(
            "/api/v1/rfps",
            params={"user_id": test_user.id, "limit": 10, "skip": 0},
        )
        assert response.status_code == 200
        assert len(response.json()) == 10

        # Test second page
        response = await client.get(
            "/api/v1/rfps",
            params={"user_id": test_user.id, "limit": 10, "skip": 10},
        )
        assert response.status_code == 200
        assert len(response.json()) == 5

    @pytest.mark.asyncio
    async def test_list_rfps_filter_by_status(
        self, client: AsyncClient, test_user: User, test_rfp: RFP
    ):
        """Test filtering RFPs by status."""
        response = await client.get(
            "/api/v1/rfps",
            params={"user_id": test_user.id, "status": "new"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        response = await client.get(
            "/api/v1/rfps",
            params={"user_id": test_user.id, "status": "analyzing"},
        )
        assert response.status_code == 200
        assert len(response.json()) == 0


class TestRFPDetail:
    """Tests for RFP detail retrieval."""

    @pytest.mark.asyncio
    async def test_get_rfp_success(self, client: AsyncClient, test_rfp: RFP):
        """Test getting RFP details."""
        response = await client.get(f"/api/v1/rfps/{test_rfp.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_rfp.id
        assert data["title"] == test_rfp.title
        assert data["solicitation_number"] == test_rfp.solicitation_number

    @pytest.mark.asyncio
    async def test_get_rfp_not_found(self, client: AsyncClient):
        """Test getting non-existent RFP."""
        response = await client.get("/api/v1/rfps/99999")
        assert response.status_code == 404


class TestRFPCreate:
    """Tests for RFP creation."""

    @pytest.mark.asyncio
    async def test_create_rfp_success(self, client: AsyncClient, test_user: User):
        """Test creating a new RFP."""
        response = await client.post(
            "/api/v1/rfps",
            params={"user_id": test_user.id},
            json={
                "title": "New Test RFP",
                "solicitation_number": "NEW-SOL-001",
                "notice_id": "new-notice-123",
                "agency": "Department of Commerce",
                "rfp_type": "solicitation",
                "classification": "fci",
                "posted_date": datetime.utcnow().isoformat(),
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Test RFP"
        assert data["solicitation_number"] == "NEW-SOL-001"
        assert data["classification"] == "fci"

    @pytest.mark.asyncio
    async def test_create_rfp_duplicate_solicitation(
        self, client: AsyncClient, test_user: User, test_rfp: RFP
    ):
        """Test creating RFP with duplicate solicitation number."""
        response = await client.post(
            "/api/v1/rfps",
            params={"user_id": test_user.id},
            json={
                "title": "Duplicate RFP",
                "solicitation_number": test_rfp.solicitation_number,
                "notice_id": "different-notice",
                "agency": "Test Agency",
                "rfp_type": "solicitation",
                "posted_date": datetime.utcnow().isoformat(),
            },
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_rfp_allows_duplicate_solicitation_for_different_user(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_rfp: RFP,
    ):
        second_user = User(
            email="rfp-second-user@example.com",
            hashed_password="hashed",
            full_name="Second User",
            company_name="Second Company",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(second_user)
        await db_session.commit()
        await db_session.refresh(second_user)

        response = await client.post(
            "/api/v1/rfps",
            params={"user_id": second_user.id},
            json={
                "title": "Second User Same Solicitation",
                "solicitation_number": test_rfp.solicitation_number,
                "agency": "Department of Energy",
                "rfp_type": "solicitation",
                "posted_date": datetime.utcnow().isoformat(),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == second_user.id
        assert data["solicitation_number"] == test_rfp.solicitation_number


class TestRFPUpdate:
    """Tests for RFP updates."""

    @pytest.mark.asyncio
    async def test_update_rfp_success(self, client: AsyncClient, test_rfp: RFP):
        """Test updating RFP fields."""
        response = await client.patch(
            f"/api/v1/rfps/{test_rfp.id}",
            json={
                "status": "analyzing",
                "is_qualified": True,
                "classification": "cui",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "analyzing"
        assert data["is_qualified"] is True
        assert data["classification"] == "cui"

    @pytest.mark.asyncio
    async def test_update_rfp_not_found(self, client: AsyncClient):
        """Test updating non-existent RFP."""
        response = await client.patch(
            "/api/v1/rfps/99999",
            json={"status": "analyzing"},
        )
        assert response.status_code == 404


class TestRFPDelete:
    """Tests for RFP deletion."""

    @pytest.mark.asyncio
    async def test_delete_rfp_success(self, client: AsyncClient, test_rfp: RFP):
        """Test deleting an RFP."""
        response = await client.delete(f"/api/v1/rfps/{test_rfp.id}")
        assert response.status_code == 200
        assert "deleted" in response.json()["message"]

        # Verify deletion
        response = await client.get(f"/api/v1/rfps/{test_rfp.id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_rfp_not_found(self, client: AsyncClient):
        """Test deleting non-existent RFP."""
        response = await client.delete("/api/v1/rfps/99999")
        assert response.status_code == 404


class TestRFPStats:
    """Tests for RFP statistics."""

    @pytest.mark.asyncio
    async def test_get_stats_empty(self, client: AsyncClient, test_user: User):
        """Test getting stats with no RFPs."""
        response = await client.get(
            "/api/v1/rfps/stats/summary",
            params={"user_id": test_user.id},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_with_data(self, client: AsyncClient, test_user: User, test_rfp: RFP):
        """Test getting stats with RFPs."""
        response = await client.get(
            "/api/v1/rfps/stats/summary",
            params={"user_id": test_user.id},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert "by_status" in data


class TestRFPAmendmentImpact:
    """Tests for amendment autopilot impact mapping."""

    @pytest.mark.asyncio
    async def test_snapshot_amendment_impact_returns_section_remediation(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_rfp: RFP,
        auth_headers: dict,
    ):
        proposal = Proposal(
            user_id=test_user.id,
            rfp_id=test_rfp.id,
            title="Cyber Ops Proposal",
            status="draft",
            total_sections=2,
            completed_sections=1,
        )
        db_session.add(proposal)
        await db_session.flush()

        impacted_section = ProposalSection(
            proposal_id=proposal.id,  # type: ignore[arg-type]
            title="Eligibility and Compliance",
            section_number="2.1",
            requirement_id="REQ-NAICS",
            requirement_text="Offeror must meet NAICS and set-aside requirements.",
            final_content=(
                "Our NAICS alignment and small-business eligibility support the revised timeline."
            ),
            display_order=1,
            status="approved",
        )
        db_session.add(impacted_section)
        db_session.add(
            ProposalSection(
                proposal_id=proposal.id,  # type: ignore[arg-type]
                title="Corporate Overview",
                section_number="1.0",
                requirement_id="REQ-INTRO",
                final_content="General company profile and background.",
                display_order=2,
                status="generated",
            )
        )

        baseline_payload = {
            "noticeId": "NOTICE-BASE",
            "solicitationNumber": test_rfp.solicitation_number,
            "title": test_rfp.title,
            "postedDate": "2026-02-01",
            "responseDeadLine": "2026-03-10",
            "organizationHierarchy": [{"name": "Department of Defense"}],
            "naicsCode": "541512",
            "typeOfSetAsideDescription": "8(a)",
            "type": "solicitation",
            "description": "Original requirement set for SOC services.",
            "resourceLinks": ["https://sam.gov/attachment/a"],
        }
        amendment_payload = {
            "noticeId": "NOTICE-BASE",
            "solicitationNumber": test_rfp.solicitation_number,
            "title": test_rfp.title,
            "postedDate": "2026-02-01",
            "responseDeadLine": "2026-03-18",
            "organizationHierarchy": [{"name": "Department of Defense"}],
            "naicsCode": "541519",
            "typeOfSetAsideDescription": "8(a)",
            "type": "solicitation",
            "description": "Amended requirement set with updated compliance scope.",
            "resourceLinks": [
                "https://sam.gov/attachment/a",
                "https://sam.gov/attachment/b",
            ],
        }
        db_session.add(
            SAMOpportunitySnapshot(
                notice_id="NOTICE-BASE",
                solicitation_number=test_rfp.solicitation_number,
                rfp_id=test_rfp.id,
                user_id=test_user.id,
                fetched_at=datetime.utcnow() - timedelta(days=1),
                posted_date=datetime.utcnow() - timedelta(days=3),
                response_deadline=datetime.utcnow() + timedelta(days=21),
                raw_hash="hash-baseline",
                raw_payload=baseline_payload,
            )
        )
        db_session.add(
            SAMOpportunitySnapshot(
                notice_id="NOTICE-BASE",
                solicitation_number=test_rfp.solicitation_number,
                rfp_id=test_rfp.id,
                user_id=test_user.id,
                fetched_at=datetime.utcnow(),
                posted_date=datetime.utcnow() - timedelta(days=3),
                response_deadline=datetime.utcnow() + timedelta(days=29),
                raw_hash="hash-amended",
                raw_payload=amendment_payload,
            )
        )
        await db_session.commit()

        response = await client.get(
            f"/api/v1/rfps/{test_rfp.id}/snapshots/amendment-impact",
            headers=auth_headers,
        )
        assert response.status_code == 200
        payload = response.json()

        assert payload["rfp_id"] == test_rfp.id
        assert "naics_code" in payload["changed_fields"]
        assert "response_deadline" in payload["changed_fields"]
        assert payload["summary"]["impacted_sections"] >= 1
        assert payload["amendment_risk_level"] in {"high", "medium"}

        impacted = payload["impacted_sections"][0]
        assert impacted["section_id"] == impacted_section.id
        assert impacted["impact_score"] >= 40
        assert impacted["approval_required"] is True

    @pytest.mark.asyncio
    async def test_snapshot_amendment_impact_requires_two_snapshots(
        self,
        client: AsyncClient,
        test_rfp: RFP,
        auth_headers: dict,
    ):
        response = await client.get(
            f"/api/v1/rfps/{test_rfp.id}/snapshots/amendment-impact",
            headers=auth_headers,
        )
        assert response.status_code == 404
        assert "Not enough snapshots" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_snapshot_amendment_impact_requires_authentication(
        self,
        client: AsyncClient,
        test_rfp: RFP,
    ):
        response = await client.get(f"/api/v1/rfps/{test_rfp.id}/snapshots/amendment-impact")
        assert response.status_code == 401
