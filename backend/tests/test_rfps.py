"""
RFP Sniper - RFP Management Tests
=================================
Tests for RFP CRUD operations.
"""

import pytest
from datetime import datetime
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.rfp import RFP


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
    async def test_list_rfps_with_data(
        self, client: AsyncClient, test_user: User, test_rfp: RFP
    ):
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
                "posted_date": datetime.utcnow().isoformat(),
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Test RFP"
        assert data["solicitation_number"] == "NEW-SOL-001"

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
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "analyzing"
        assert data["is_qualified"] is True

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
    async def test_get_stats_with_data(
        self, client: AsyncClient, test_user: User, test_rfp: RFP
    ):
        """Test getting stats with RFPs."""
        response = await client.get(
            "/api/v1/rfps/stats/summary",
            params={"user_id": test_user.id},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert "by_status" in data
