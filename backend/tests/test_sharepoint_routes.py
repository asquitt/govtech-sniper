"""
Integration tests for sharepoint.py:
  - GET  /sharepoint/browse
  - GET  /sharepoint/download/{file_id}
  - POST /sharepoint/upload
  - POST /sharepoint/export
  - GET  /sharepoint/status
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration import IntegrationConfig, IntegrationProvider
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password


@pytest.fixture
async def sp_integration(db_session: AsyncSession, test_user: User) -> IntegrationConfig:
    """Create a SharePoint integration config."""
    integration = IntegrationConfig(
        user_id=test_user.id,
        provider=IntegrationProvider.SHAREPOINT,
        name="Test SP",
        is_enabled=True,
        config={
            "site_url": "https://test.sharepoint.com",
            "tenant_id": "tenant-123",
            "client_id": "client-123",
            "client_secret": "secret-123",
        },
    )
    db_session.add(integration)
    await db_session.commit()
    await db_session.refresh(integration)
    return integration


class TestSharePointStatus:
    """Tests for GET /api/v1/sharepoint/status."""

    @pytest.mark.asyncio
    async def test_status_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/sharepoint/status")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_status_no_config(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.get("/api/v1/sharepoint/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["configured"] is False

    @pytest.mark.asyncio
    async def test_status_with_config(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sp_integration: IntegrationConfig,
        test_user: User,
    ):
        response = await client.get("/api/v1/sharepoint/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["configured"] is True


class TestSharePointBrowse:
    """Tests for GET /api/v1/sharepoint/browse."""

    @pytest.mark.asyncio
    async def test_browse_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/sharepoint/browse")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_browse_no_integration(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.get("/api/v1/sharepoint/browse", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_browse_with_integration(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sp_integration: IntegrationConfig,
        test_user: User,
    ):
        """Will fail since SP service is fake, but should get a clear error."""
        response = await client.get("/api/v1/sharepoint/browse", headers=auth_headers)
        assert response.status_code in (200, 400, 502)


class TestSharePointDownload:
    """Tests for GET /api/v1/sharepoint/download/{file_id}."""

    @pytest.mark.asyncio
    async def test_download_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/sharepoint/download/abc123")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_download_no_integration(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.get("/api/v1/sharepoint/download/abc123", headers=auth_headers)
        assert response.status_code == 404


class TestSharePointUpload:
    """Tests for POST /api/v1/sharepoint/upload."""

    @pytest.mark.asyncio
    async def test_upload_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/sharepoint/upload?folder=/test&name=file.txt")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_upload_no_integration(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.post(
            "/api/v1/sharepoint/upload?folder=/test&name=file.txt",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestSharePointExport:
    """Tests for POST /api/v1/sharepoint/export."""

    @pytest.mark.asyncio
    async def test_export_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/sharepoint/export?proposal_id=1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_export_proposal_not_found(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.post(
            "/api/v1/sharepoint/export?proposal_id=99999",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_export_idor(
        self,
        client: AsyncClient,
        test_proposal,
        db_session: AsyncSession,
    ):
        other = User(
            email="other@example.com",
            hashed_password=hash_password("OtherPass123!"),
            full_name="Other",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other)
        await db_session.commit()
        await db_session.refresh(other)
        tokens = create_token_pair(other.id, other.email, other.tier)
        headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.post(
            f"/api/v1/sharepoint/export?proposal_id={test_proposal.id}",
            headers=headers,
        )
        assert response.status_code == 404
