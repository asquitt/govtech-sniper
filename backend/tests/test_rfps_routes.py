"""
Tests for RFP routes - CRUD operations.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rfp import RFP, RFPStatus
from app.models.user import User
from app.services.auth_service import create_token_pair


@pytest_asyncio.fixture
async def owned_rfp(db_session: AsyncSession, test_user: User) -> RFP:
    rfp = RFP(
        user_id=test_user.id,
        title="Test RFP",
        solicitation_number="SOL-2025-001",
        agency="Test Agency",
        status=RFPStatus.NEW,
    )
    db_session.add(rfp)
    await db_session.commit()
    await db_session.refresh(rfp)
    return rfp


class TestListRFPs:
    """Tests for GET /api/v1/rfps."""

    @pytest.mark.asyncio
    async def test_list_rfps_unauthenticated(self, client: AsyncClient):
        response = await client.get("/api/v1/rfps")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_rfps_empty(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/rfps", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_rfps_returns_owned(
        self, client: AsyncClient, auth_headers: dict, owned_rfp: RFP
    ):
        response = await client.get("/api/v1/rfps", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["title"] == "Test RFP"

    @pytest.mark.asyncio
    async def test_list_rfps_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        owned_rfp: RFP,
    ):
        other = User(
            email="other_rfp@example.com",
            hashed_password="hashed",
            full_name="Other",
            tier="free",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other)
        await db_session.commit()
        await db_session.refresh(other)
        tokens = create_token_pair(other.id, other.email, other.tier)
        headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.get("/api/v1/rfps", headers=headers)
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_rfps_filter_status(
        self, client: AsyncClient, auth_headers: dict, owned_rfp: RFP
    ):
        response = await client.get("/api/v1/rfps", headers=auth_headers, params={"status": "new"})
        assert response.status_code == 200
        assert len(response.json()) >= 1

    @pytest.mark.asyncio
    async def test_list_rfps_pagination(
        self, client: AsyncClient, auth_headers: dict, owned_rfp: RFP
    ):
        response = await client.get(
            "/api/v1/rfps", headers=auth_headers, params={"skip": 0, "limit": 1}
        )
        assert response.status_code == 200


class TestGetRFP:
    """Tests for GET /api/v1/rfps/{rfp_id}."""

    @pytest.mark.asyncio
    async def test_get_rfp_unauthenticated(self, client: AsyncClient, owned_rfp: RFP):
        response = await client.get(f"/api/v1/rfps/{owned_rfp.id}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_rfp_success(self, client: AsyncClient, auth_headers: dict, owned_rfp: RFP):
        response = await client.get(f"/api/v1/rfps/{owned_rfp.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test RFP"
        assert data["solicitation_number"] == "SOL-2025-001"

    @pytest.mark.asyncio
    async def test_get_rfp_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/rfps/99999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_rfp_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        owned_rfp: RFP,
    ):
        other = User(
            email="idor_rfp@example.com",
            hashed_password="hashed",
            full_name="Other",
            tier="free",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other)
        await db_session.commit()
        await db_session.refresh(other)
        tokens = create_token_pair(other.id, other.email, other.tier)
        headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.get(f"/api/v1/rfps/{owned_rfp.id}", headers=headers)
        assert response.status_code == 404


class TestCreateRFP:
    """Tests for POST /api/v1/rfps."""

    @pytest.mark.asyncio
    async def test_create_rfp_unauthenticated(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/rfps",
            json={
                "title": "New RFP",
                "solicitation_number": "NEW-001",
                "agency": "Agency",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_rfp_success(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/rfps",
            headers=auth_headers,
            json={
                "title": "Created RFP",
                "solicitation_number": "CREATE-001",
                "agency": "Test Agency",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Created RFP"
        assert data["solicitation_number"] == "CREATE-001"

    @pytest.mark.asyncio
    async def test_create_rfp_duplicate_solicitation(
        self, client: AsyncClient, auth_headers: dict, owned_rfp: RFP
    ):
        response = await client.post(
            "/api/v1/rfps",
            headers=auth_headers,
            json={
                "title": "Duplicate",
                "solicitation_number": "SOL-2025-001",
                "agency": "Agency",
            },
        )
        assert response.status_code == 409


class TestUpdateRFP:
    """Tests for PATCH /api/v1/rfps/{rfp_id}."""

    @pytest.mark.asyncio
    async def test_update_rfp_unauthenticated(self, client: AsyncClient, owned_rfp: RFP):
        response = await client.patch(
            f"/api/v1/rfps/{owned_rfp.id}",
            json={"title": "Updated"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_rfp_success(
        self, client: AsyncClient, auth_headers: dict, owned_rfp: RFP
    ):
        response = await client.patch(
            f"/api/v1/rfps/{owned_rfp.id}",
            headers=auth_headers,
            json={"title": "Updated Title"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"

    @pytest.mark.asyncio
    async def test_update_rfp_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.patch(
            "/api/v1/rfps/99999",
            headers=auth_headers,
            json={"title": "Updated"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_rfp_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        owned_rfp: RFP,
    ):
        other = User(
            email="idor_update@example.com",
            hashed_password="hashed",
            full_name="Other",
            tier="free",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other)
        await db_session.commit()
        await db_session.refresh(other)
        tokens = create_token_pair(other.id, other.email, other.tier)
        headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.patch(
            f"/api/v1/rfps/{owned_rfp.id}",
            headers=headers,
            json={"title": "Hacked"},
        )
        assert response.status_code == 404


class TestDeleteRFP:
    """Tests for DELETE /api/v1/rfps/{rfp_id}."""

    @pytest.mark.asyncio
    async def test_delete_rfp_unauthenticated(self, client: AsyncClient, owned_rfp: RFP):
        response = await client.delete(f"/api/v1/rfps/{owned_rfp.id}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_rfp_success(
        self, client: AsyncClient, auth_headers: dict, owned_rfp: RFP
    ):
        response = await client.delete(f"/api/v1/rfps/{owned_rfp.id}", headers=auth_headers)
        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_delete_rfp_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.delete("/api/v1/rfps/99999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_rfp_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        owned_rfp: RFP,
    ):
        other = User(
            email="idor_delete@example.com",
            hashed_password="hashed",
            full_name="Other",
            tier="free",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other)
        await db_session.commit()
        await db_session.refresh(other)
        tokens = create_token_pair(other.id, other.email, other.tier)
        headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.delete(f"/api/v1/rfps/{owned_rfp.id}", headers=headers)
        assert response.status_code == 404


class TestRFPStats:
    """Tests for GET /api/v1/rfps/stats/summary."""

    @pytest.mark.asyncio
    async def test_stats_unauthenticated(self, client: AsyncClient):
        response = await client.get("/api/v1/rfps/stats/summary")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_stats_empty(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/rfps/stats/summary", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_stats_with_rfps(self, client: AsyncClient, auth_headers: dict, owned_rfp: RFP):
        response = await client.get("/api/v1/rfps/stats/summary", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert "by_status" in data


class TestUploadPDF:
    """Tests for POST /api/v1/rfps/{rfp_id}/upload-pdf."""

    @pytest.mark.asyncio
    async def test_upload_pdf_not_implemented(
        self, client: AsyncClient, auth_headers: dict, owned_rfp: RFP
    ):
        response = await client.post(
            f"/api/v1/rfps/{owned_rfp.id}/upload-pdf", headers=auth_headers
        )
        assert response.status_code == 501
