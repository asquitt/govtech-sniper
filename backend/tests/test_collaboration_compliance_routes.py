"""
Tests for collaboration/compliance routes - Compliance digest scheduling, preview, send.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.collaboration import SharedWorkspace, WorkspaceMember, WorkspaceRole
from app.models.user import User
from app.services.auth_service import create_token_pair


@pytest_asyncio.fixture
async def ws_owner(db_session: AsyncSession) -> User:
    user = User(
        email="digest_owner@example.com",
        hashed_password="hashed",
        full_name="Digest Owner",
        tier="professional",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def ws_owner_headers(ws_owner: User) -> dict:
    tokens = create_token_pair(ws_owner.id, ws_owner.email, ws_owner.tier)
    return {"Authorization": f"Bearer {tokens.access_token}"}


@pytest_asyncio.fixture
async def test_workspace(db_session: AsyncSession, ws_owner: User) -> SharedWorkspace:
    ws = SharedWorkspace(owner_id=ws_owner.id, name="Digest Test WS")
    db_session.add(ws)
    await db_session.commit()
    await db_session.refresh(ws)
    return ws


@pytest_asyncio.fixture
async def viewer_user(db_session: AsyncSession) -> User:
    user = User(
        email="digest_viewer@example.com",
        hashed_password="hashed",
        full_name="Digest Viewer",
        tier="professional",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def viewer_membership(
    db_session: AsyncSession,
    test_workspace: SharedWorkspace,
    viewer_user: User,
) -> WorkspaceMember:
    member = WorkspaceMember(
        workspace_id=test_workspace.id,
        user_id=viewer_user.id,
        role=WorkspaceRole.VIEWER,
    )
    db_session.add(member)
    await db_session.commit()
    return member


@pytest_asyncio.fixture
async def viewer_headers(viewer_user: User) -> dict:
    tokens = create_token_pair(viewer_user.id, viewer_user.email, viewer_user.tier)
    return {"Authorization": f"Bearer {tokens.access_token}"}


class TestGetDigestSchedule:
    """Tests for GET /api/v1/collaboration/workspaces/{workspace_id}/compliance-digest-schedule."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self, client: AsyncClient, test_workspace: SharedWorkspace
    ):
        response = await client.get(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/compliance-digest-schedule",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_schedule_creates_default(
        self,
        client: AsyncClient,
        ws_owner_headers: dict,
        test_workspace: SharedWorkspace,
    ):
        response = await client.get(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/compliance-digest-schedule",
            headers=ws_owner_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["workspace_id"] == test_workspace.id
        assert data["frequency"] == "weekly"
        assert data["channel"] == "in_app"
        assert data["is_enabled"] is True

    @pytest.mark.asyncio
    async def test_viewer_cannot_access_schedule(
        self,
        client: AsyncClient,
        viewer_headers: dict,
        test_workspace: SharedWorkspace,
        viewer_membership: WorkspaceMember,
    ):
        response = await client.get(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/compliance-digest-schedule",
            headers=viewer_headers,
        )
        assert response.status_code == 403


class TestUpdateDigestSchedule:
    """Tests for PATCH /api/v1/collaboration/workspaces/{workspace_id}/compliance-digest-schedule."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self, client: AsyncClient, test_workspace: SharedWorkspace
    ):
        response = await client.patch(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/compliance-digest-schedule",
            json={
                "frequency": "daily",
                "hour_utc": 9,
                "minute_utc": 0,
                "channel": "email",
                "recipient_role": "admin",
                "anomalies_only": True,
                "is_enabled": True,
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_schedule_success(
        self,
        client: AsyncClient,
        ws_owner_headers: dict,
        test_workspace: SharedWorkspace,
    ):
        response = await client.patch(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/compliance-digest-schedule",
            headers=ws_owner_headers,
            json={
                "frequency": "daily",
                "hour_utc": 15,
                "minute_utc": 30,
                "channel": "email",
                "recipient_role": "admin",
                "anomalies_only": True,
                "is_enabled": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["frequency"] == "daily"
        assert data["hour_utc"] == 15
        assert data["minute_utc"] == 30
        assert data["channel"] == "email"
        assert data["anomalies_only"] is True

    @pytest.mark.asyncio
    async def test_invalid_frequency_returns_400(
        self,
        client: AsyncClient,
        ws_owner_headers: dict,
        test_workspace: SharedWorkspace,
    ):
        response = await client.patch(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/compliance-digest-schedule",
            headers=ws_owner_headers,
            json={
                "frequency": "invalid",
                "hour_utc": 9,
                "minute_utc": 0,
                "channel": "in_app",
                "recipient_role": "all",
                "anomalies_only": False,
                "is_enabled": True,
            },
        )
        assert response.status_code == 400


class TestDigestPreview:
    """Tests for GET /api/v1/collaboration/workspaces/{workspace_id}/compliance-digest-preview."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self, client: AsyncClient, test_workspace: SharedWorkspace
    ):
        response = await client.get(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/compliance-digest-preview",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_preview_success(
        self,
        client: AsyncClient,
        ws_owner_headers: dict,
        test_workspace: SharedWorkspace,
    ):
        response = await client.get(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/compliance-digest-preview",
            headers=ws_owner_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["workspace_id"] == test_workspace.id
        assert "summary" in data
        assert "trends" in data
        assert "anomalies" in data
        assert "schedule" in data
        assert "delivery_summary" in data
        assert "recipient_count" in data


class TestSendDigest:
    """Tests for POST /api/v1/collaboration/workspaces/{workspace_id}/compliance-digest-send."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self, client: AsyncClient, test_workspace: SharedWorkspace
    ):
        response = await client.post(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/compliance-digest-send",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_send_digest_success(
        self,
        client: AsyncClient,
        ws_owner_headers: dict,
        test_workspace: SharedWorkspace,
    ):
        # First ensure a schedule exists (GET auto-creates)
        await client.get(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/compliance-digest-schedule",
            headers=ws_owner_headers,
        )
        response = await client.post(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/compliance-digest-send",
            headers=ws_owner_headers,
        )
        # Owner is always counted as recipient=1
        assert response.status_code == 200
        data = response.json()
        assert data["workspace_id"] == test_workspace.id
        assert "delivery_summary" in data

    @pytest.mark.asyncio
    async def test_send_disabled_schedule_returns_400(
        self,
        client: AsyncClient,
        ws_owner_headers: dict,
        test_workspace: SharedWorkspace,
    ):
        # Create schedule, then disable it
        await client.patch(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/compliance-digest-schedule",
            headers=ws_owner_headers,
            json={
                "frequency": "weekly",
                "hour_utc": 9,
                "minute_utc": 0,
                "channel": "in_app",
                "recipient_role": "all",
                "anomalies_only": False,
                "is_enabled": False,
            },
        )
        response = await client.post(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/compliance-digest-send",
            headers=ws_owner_headers,
        )
        assert response.status_code == 400


class TestListDigestDeliveries:
    """Tests for GET /api/v1/collaboration/workspaces/{workspace_id}/compliance-digest-deliveries."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self, client: AsyncClient, test_workspace: SharedWorkspace
    ):
        response = await client.get(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/compliance-digest-deliveries",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_deliveries_empty(
        self,
        client: AsyncClient,
        ws_owner_headers: dict,
        test_workspace: SharedWorkspace,
    ):
        response = await client.get(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/compliance-digest-deliveries",
            headers=ws_owner_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["workspace_id"] == test_workspace.id
        assert isinstance(data["items"], list)
        assert "summary" in data

    @pytest.mark.asyncio
    async def test_list_deliveries_after_send(
        self,
        client: AsyncClient,
        ws_owner_headers: dict,
        test_workspace: SharedWorkspace,
    ):
        # Create schedule + send
        await client.get(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/compliance-digest-schedule",
            headers=ws_owner_headers,
        )
        await client.post(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/compliance-digest-send",
            headers=ws_owner_headers,
        )

        response = await client.get(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/compliance-digest-deliveries",
            headers=ws_owner_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 1
        assert data["summary"]["success_count"] >= 1
