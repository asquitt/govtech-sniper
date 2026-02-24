"""
Tests for collaboration/invitations routes - Workspace invitations.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.collaboration import (
    SharedWorkspace,
    WorkspaceInvitation,
    WorkspaceMember,
    WorkspaceRole,
)
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
        name="Invite Test Workspace",
    )
    db_session.add(ws)
    await db_session.commit()
    await db_session.refresh(ws)
    return ws


@pytest_asyncio.fixture
async def invitee_user(db_session: AsyncSession) -> User:
    user = User(
        email="invitee@example.com",
        hashed_password="hashed",
        full_name="Invitee",
        tier="professional",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def invitee_headers(invitee_user: User) -> dict:
    tokens = create_token_pair(invitee_user.id, invitee_user.email, invitee_user.tier)
    return {"Authorization": f"Bearer {tokens.access_token}"}


@pytest_asyncio.fixture
async def test_invitation(
    db_session: AsyncSession,
    test_workspace: SharedWorkspace,
    invitee_user: User,
) -> WorkspaceInvitation:
    from datetime import datetime, timedelta

    invite = WorkspaceInvitation(
        workspace_id=test_workspace.id,
        email=invitee_user.email,
        role=WorkspaceRole.CONTRIBUTOR,
        token="test-token-123",
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db_session.add(invite)
    await db_session.commit()
    await db_session.refresh(invite)
    return invite


class TestInviteToWorkspace:
    """Tests for POST /api/v1/collaboration/workspaces/{workspace_id}/invite."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self, client: AsyncClient, test_workspace: SharedWorkspace
    ):
        response = await client.post(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/invite",
            json={"email": "someone@example.com", "role": "viewer"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invite_success_as_owner(
        self,
        client: AsyncClient,
        ws_owner_headers: dict,
        test_workspace: SharedWorkspace,
    ):
        response = await client.post(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/invite",
            headers=ws_owner_headers,
            json={"email": "newmember@example.com", "role": "viewer"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newmember@example.com"
        assert data["role"] == "viewer"
        assert "accept_token" in data

    @pytest.mark.asyncio
    async def test_non_admin_cannot_invite(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_workspace: SharedWorkspace,
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

        membership = WorkspaceMember(
            workspace_id=test_workspace.id,
            user_id=viewer.id,
            role=WorkspaceRole.VIEWER,
        )
        db_session.add(membership)
        await db_session.commit()

        tokens = create_token_pair(viewer.id, viewer.email, viewer.tier)
        headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.post(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/invite",
            headers=headers,
            json={"email": "new@example.com", "role": "viewer"},
        )
        assert response.status_code == 403


class TestListInvitations:
    """Tests for GET /api/v1/collaboration/workspaces/{workspace_id}/invitations."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self, client: AsyncClient, test_workspace: SharedWorkspace
    ):
        response = await client.get(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/invitations",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_invitations_success(
        self,
        client: AsyncClient,
        ws_owner_headers: dict,
        test_workspace: SharedWorkspace,
        test_invitation: WorkspaceInvitation,
    ):
        response = await client.get(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/invitations",
            headers=ws_owner_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["email"] == "invitee@example.com"

    @pytest.mark.asyncio
    async def test_list_invitations_empty(
        self,
        client: AsyncClient,
        ws_owner_headers: dict,
        test_workspace: SharedWorkspace,
    ):
        response = await client.get(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/invitations",
            headers=ws_owner_headers,
        )
        assert response.status_code == 200
        assert response.json() == []


class TestAcceptInvitation:
    """Tests for POST /api/v1/collaboration/invitations/accept."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/collaboration/invitations/accept",
            params={"token": "test-token"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_accept_invitation_success(
        self,
        client: AsyncClient,
        invitee_headers: dict,
        test_invitation: WorkspaceInvitation,
    ):
        response = await client.post(
            "/api/v1/collaboration/invitations/accept",
            headers=invitee_headers,
            params={"token": test_invitation.token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "contributor"
        assert data["user_email"] == "invitee@example.com"

    @pytest.mark.asyncio
    async def test_accept_invalid_token_returns_404(
        self, client: AsyncClient, invitee_headers: dict
    ):
        response = await client.post(
            "/api/v1/collaboration/invitations/accept",
            headers=invitee_headers,
            params={"token": "nonexistent-token"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_accept_wrong_email_returns_403(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_invitation: WorkspaceInvitation,
    ):
        # auth_headers belongs to test_user (different email)
        response = await client.post(
            "/api/v1/collaboration/invitations/accept",
            headers=auth_headers,
            params={"token": test_invitation.token},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_accept_already_accepted_returns_400(
        self,
        client: AsyncClient,
        invitee_headers: dict,
        test_invitation: WorkspaceInvitation,
    ):
        # Accept once
        await client.post(
            "/api/v1/collaboration/invitations/accept",
            headers=invitee_headers,
            params={"token": test_invitation.token},
        )
        # Accept again
        response = await client.post(
            "/api/v1/collaboration/invitations/accept",
            headers=invitee_headers,
            params={"token": test_invitation.token},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_owner_cannot_accept_returns_400(
        self,
        client: AsyncClient,
        ws_owner_headers: dict,
        db_session: AsyncSession,
        test_workspace: SharedWorkspace,
        ws_owner: User,
    ):
        from datetime import datetime, timedelta

        invite = WorkspaceInvitation(
            workspace_id=test_workspace.id,
            email=ws_owner.email,
            role=WorkspaceRole.VIEWER,
            token="owner-token-123",
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        db_session.add(invite)
        await db_session.commit()

        response = await client.post(
            "/api/v1/collaboration/invitations/accept",
            headers=ws_owner_headers,
            params={"token": "owner-token-123"},
        )
        assert response.status_code == 400
