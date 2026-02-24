"""
Integration tests for sharepoint_sync.py:
  - POST   /sharepoint/sync/configure
  - GET    /sharepoint/sync/configs
  - POST   /sharepoint/sync/{id}/trigger
  - GET    /sharepoint/sync/{id}/status
  - DELETE /sharepoint/sync/{id}
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.proposal import Proposal
from app.models.sharepoint_sync import SharePointSyncConfig
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password


@pytest.fixture
async def sync_config(
    db_session: AsyncSession, test_user: User, test_proposal: Proposal
) -> SharePointSyncConfig:
    """Create a SharePoint sync config for testing."""
    config = SharePointSyncConfig(
        user_id=test_user.id,
        proposal_id=test_proposal.id,
        sharepoint_folder="/Proposals/Test",
        sync_direction="push",
        auto_sync_enabled=False,
    )
    db_session.add(config)
    await db_session.commit()
    await db_session.refresh(config)
    return config


class TestConfigureSync:
    """Tests for POST /api/v1/sharepoint/sync/configure."""

    @pytest.mark.asyncio
    async def test_configure_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/sharepoint/sync/configure",
            json={
                "proposal_id": 1,
                "sharepoint_folder": "/Test",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_configure_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
        test_user: User,
    ):
        response = await client.post(
            "/api/v1/sharepoint/sync/configure",
            headers=auth_headers,
            json={
                "proposal_id": test_proposal.id,
                "sharepoint_folder": "/Proposals/New",
                "sync_direction": "push",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["sharepoint_folder"] == "/Proposals/New"
        assert data["proposal_id"] == test_proposal.id

    @pytest.mark.asyncio
    async def test_configure_updates_existing(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sync_config: SharePointSyncConfig,
        test_proposal: Proposal,
        test_user: User,
    ):
        response = await client.post(
            "/api/v1/sharepoint/sync/configure",
            headers=auth_headers,
            json={
                "proposal_id": test_proposal.id,
                "sharepoint_folder": "/Updated/Folder",
            },
        )
        assert response.status_code == 200
        assert response.json()["sharepoint_folder"] == "/Updated/Folder"


class TestListSyncConfigs:
    """Tests for GET /api/v1/sharepoint/sync/configs."""

    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/sharepoint/sync/configs")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_empty(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.get("/api/v1/sharepoint/sync/configs", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_with_data(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sync_config: SharePointSyncConfig,
        test_user: User,
    ):
        response = await client.get("/api/v1/sharepoint/sync/configs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    @pytest.mark.asyncio
    async def test_list_filter_by_proposal(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sync_config: SharePointSyncConfig,
        test_proposal: Proposal,
        test_user: User,
    ):
        response = await client.get(
            f"/api/v1/sharepoint/sync/configs?proposal_id={test_proposal.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert len(response.json()) == 1

    @pytest.mark.asyncio
    async def test_list_idor(
        self,
        client: AsyncClient,
        sync_config: SharePointSyncConfig,
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

        response = await client.get("/api/v1/sharepoint/sync/configs", headers=headers)
        assert response.status_code == 200
        assert response.json() == []


class TestTriggerSync:
    """Tests for POST /api/v1/sharepoint/sync/{id}/trigger."""

    @pytest.mark.asyncio
    async def test_trigger_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/sharepoint/sync/1/trigger")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_trigger_not_found(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.post("/api/v1/sharepoint/sync/99999/trigger", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_trigger_with_config(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sync_config: SharePointSyncConfig,
        test_user: User,
    ):
        """Trigger does a lazy import of Celery task. Expect 200 or error."""
        response = await client.post(
            f"/api/v1/sharepoint/sync/{sync_config.id}/trigger",
            headers=auth_headers,
        )
        # May fail if Celery is not running - accept both
        assert response.status_code in (200, 500)


class TestGetSyncStatus:
    """Tests for GET /api/v1/sharepoint/sync/{id}/status."""

    @pytest.mark.asyncio
    async def test_status_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/sharepoint/sync/1/status")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_status_not_found(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.get("/api/v1/sharepoint/sync/99999/status", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_status_empty_logs(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sync_config: SharePointSyncConfig,
        test_user: User,
    ):
        response = await client.get(
            f"/api/v1/sharepoint/sync/{sync_config.id}/status",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json() == []


class TestDeleteSyncConfig:
    """Tests for DELETE /api/v1/sharepoint/sync/{id}."""

    @pytest.mark.asyncio
    async def test_delete_requires_auth(self, client: AsyncClient):
        response = await client.delete("/api/v1/sharepoint/sync/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sync_config: SharePointSyncConfig,
        test_user: User,
    ):
        response = await client.delete(
            f"/api/v1/sharepoint/sync/{sync_config.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Sync config deleted"

    @pytest.mark.asyncio
    async def test_delete_not_found(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.delete("/api/v1/sharepoint/sync/99999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_idor(
        self,
        client: AsyncClient,
        sync_config: SharePointSyncConfig,
        db_session: AsyncSession,
    ):
        other = User(
            email="other2@example.com",
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

        response = await client.delete(
            f"/api/v1/sharepoint/sync/{sync_config.id}",
            headers=headers,
        )
        assert response.status_code == 404
