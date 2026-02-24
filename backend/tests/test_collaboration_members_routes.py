"""
Tests for collaboration/members routes - Workspace member management.
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
    ws = SharedWorkspace(owner_id=ws_owner.id, name="Members Test WS")
    db_session.add(ws)
    await db_session.commit()
    await db_session.refresh(ws)
    return ws


@pytest_asyncio.fixture
async def member_user(db_session: AsyncSession) -> User:
    user = User(
        email="member@example.com",
        hashed_password="hashed",
        full_name="Member User",
        tier="professional",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_membership(
    db_session: AsyncSession,
    test_workspace: SharedWorkspace,
    member_user: User,
) -> WorkspaceMember:
    member = WorkspaceMember(
        workspace_id=test_workspace.id,
        user_id=member_user.id,
        role=WorkspaceRole.CONTRIBUTOR,
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(member)
    return member


class TestListMembers:
    """Tests for GET /api/v1/collaboration/workspaces/{workspace_id}/members."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self, client: AsyncClient, test_workspace: SharedWorkspace
    ):
        response = await client.get(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/members",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_members_as_owner(
        self,
        client: AsyncClient,
        ws_owner_headers: dict,
        test_workspace: SharedWorkspace,
        test_membership: WorkspaceMember,
    ):
        response = await client.get(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/members",
            headers=ws_owner_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        emails = [m["user_email"] for m in data]
        assert "member@example.com" in emails

    @pytest.mark.asyncio
    async def test_non_member_returns_403(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_workspace: SharedWorkspace,
    ):
        response = await client.get(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/members",
            headers=auth_headers,
        )
        assert response.status_code == 403


class TestUpdateMemberRole:
    """Tests for PATCH /api/v1/collaboration/workspaces/{workspace_id}/members/{member_id}/role."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self,
        client: AsyncClient,
        test_workspace: SharedWorkspace,
        test_membership: WorkspaceMember,
    ):
        response = await client.patch(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/members/{test_membership.id}/role",
            json={"role": "admin"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_role_as_owner(
        self,
        client: AsyncClient,
        ws_owner_headers: dict,
        test_workspace: SharedWorkspace,
        test_membership: WorkspaceMember,
    ):
        response = await client.patch(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/members/{test_membership.id}/role",
            headers=ws_owner_headers,
            json={"role": "admin"},
        )
        assert response.status_code == 200
        assert response.json()["role"] == "admin"

    @pytest.mark.asyncio
    async def test_member_not_found(
        self,
        client: AsyncClient,
        ws_owner_headers: dict,
        test_workspace: SharedWorkspace,
    ):
        response = await client.patch(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/members/99999/role",
            headers=ws_owner_headers,
            json={"role": "viewer"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_non_admin_cannot_update_role(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_workspace: SharedWorkspace,
        test_membership: WorkspaceMember,
    ):
        viewer = User(
            email="viewer@example.com",
            hashed_password="hashed",
            full_name="Viewer",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(viewer)
        await db_session.commit()
        await db_session.refresh(viewer)

        viewer_member = WorkspaceMember(
            workspace_id=test_workspace.id,
            user_id=viewer.id,
            role=WorkspaceRole.VIEWER,
        )
        db_session.add(viewer_member)
        await db_session.commit()

        tokens = create_token_pair(viewer.id, viewer.email, viewer.tier)
        headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.patch(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/members/{test_membership.id}/role",
            headers=headers,
            json={"role": "admin"},
        )
        assert response.status_code == 403


class TestRemoveMember:
    """Tests for DELETE /api/v1/collaboration/workspaces/{workspace_id}/members/{member_id}."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self,
        client: AsyncClient,
        test_workspace: SharedWorkspace,
        test_membership: WorkspaceMember,
    ):
        response = await client.delete(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/members/{test_membership.id}",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_remove_member_as_owner(
        self,
        client: AsyncClient,
        ws_owner_headers: dict,
        test_workspace: SharedWorkspace,
        test_membership: WorkspaceMember,
    ):
        response = await client.delete(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/members/{test_membership.id}",
            headers=ws_owner_headers,
        )
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_member_not_found(
        self,
        client: AsyncClient,
        ws_owner_headers: dict,
        test_workspace: SharedWorkspace,
    ):
        response = await client.delete(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/members/99999",
            headers=ws_owner_headers,
        )
        assert response.status_code == 404
