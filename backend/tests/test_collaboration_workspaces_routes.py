"""
Tests for collaboration/workspaces routes - Workspace CRUD.
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
        email="wsowner@example.com",
        hashed_password="hashed",
        full_name="WS Owner",
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
    ws = SharedWorkspace(
        owner_id=ws_owner.id,
        name="Test Workspace",
        description="For testing",
    )
    db_session.add(ws)
    await db_session.commit()
    await db_session.refresh(ws)
    return ws


class TestListWorkspaces:
    """Tests for GET /api/v1/collaboration/workspaces."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        response = await client.get("/api/v1/collaboration/workspaces")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_owned_workspaces(
        self,
        client: AsyncClient,
        ws_owner_headers: dict,
        test_workspace: SharedWorkspace,
    ):
        response = await client.get(
            "/api/v1/collaboration/workspaces",
            headers=ws_owner_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["name"] == "Test Workspace"

    @pytest.mark.asyncio
    async def test_list_member_workspaces(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_workspace: SharedWorkspace,
    ):
        member_user = User(
            email="member@example.com",
            hashed_password="hashed",
            full_name="Member",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(member_user)
        await db_session.commit()
        await db_session.refresh(member_user)

        membership = WorkspaceMember(
            workspace_id=test_workspace.id,
            user_id=member_user.id,
            role=WorkspaceRole.VIEWER,
        )
        db_session.add(membership)
        await db_session.commit()

        tokens = create_token_pair(member_user.id, member_user.email, member_user.tier)
        headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.get("/api/v1/collaboration/workspaces", headers=headers)
        assert response.status_code == 200
        names = [w["name"] for w in response.json()]
        assert "Test Workspace" in names

    @pytest.mark.asyncio
    async def test_list_empty(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(
            "/api/v1/collaboration/workspaces",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json() == []


class TestCreateWorkspace:
    """Tests for POST /api/v1/collaboration/workspaces."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/collaboration/workspaces",
            json={"name": "New WS"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_workspace_success(self, client: AsyncClient, ws_owner_headers: dict):
        response = await client.post(
            "/api/v1/collaboration/workspaces",
            headers=ws_owner_headers,
            json={"name": "My Workspace", "description": "Testing creation"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "My Workspace"
        assert data["description"] == "Testing creation"
        assert data["member_count"] == 0

    @pytest.mark.asyncio
    async def test_create_workspace_with_rfp(
        self, client: AsyncClient, ws_owner_headers: dict, test_rfp
    ):
        response = await client.post(
            "/api/v1/collaboration/workspaces",
            headers=ws_owner_headers,
            json={"name": "RFP WS", "rfp_id": test_rfp.id},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["rfp_id"] == test_rfp.id


class TestUpdateWorkspace:
    """Tests for PATCH /api/v1/collaboration/workspaces/{workspace_id}."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self, client: AsyncClient, test_workspace: SharedWorkspace
    ):
        response = await client.patch(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}",
            json={"name": "Updated"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_workspace_success(
        self,
        client: AsyncClient,
        ws_owner_headers: dict,
        test_workspace: SharedWorkspace,
    ):
        response = await client.patch(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}",
            headers=ws_owner_headers,
            json={"name": "Updated Name"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_non_owner_cannot_update(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_workspace: SharedWorkspace,
    ):
        response = await client.patch(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}",
            headers=auth_headers,
            json={"name": "Hacked"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_workspace_not_found(self, client: AsyncClient, ws_owner_headers: dict):
        response = await client.patch(
            "/api/v1/collaboration/workspaces/99999",
            headers=ws_owner_headers,
            json={"name": "Updated"},
        )
        assert response.status_code == 404


class TestDeleteWorkspace:
    """Tests for DELETE /api/v1/collaboration/workspaces/{workspace_id}."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self, client: AsyncClient, test_workspace: SharedWorkspace
    ):
        response = await client.delete(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_workspace_success(
        self,
        client: AsyncClient,
        ws_owner_headers: dict,
        test_workspace: SharedWorkspace,
    ):
        response = await client.delete(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}",
            headers=ws_owner_headers,
        )
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_non_owner_cannot_delete(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_workspace: SharedWorkspace,
    ):
        response = await client.delete(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}",
            headers=auth_headers,
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_workspace_not_found(self, client: AsyncClient, ws_owner_headers: dict):
        response = await client.delete(
            "/api/v1/collaboration/workspaces/99999",
            headers=ws_owner_headers,
        )
        assert response.status_code == 404
