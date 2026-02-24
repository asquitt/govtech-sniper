"""
Tests for collaboration/portal routes - Partner portal read-only view.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.collaboration import (
    ShareApprovalStatus,
    SharedDataPermission,
    SharedDataType,
    SharedWorkspace,
    WorkspaceMember,
    WorkspaceRole,
)
from app.models.user import User
from app.services.auth_service import create_token_pair


@pytest_asyncio.fixture
async def ws_owner(db_session: AsyncSession) -> User:
    user = User(
        email="portal_owner@example.com",
        hashed_password="hashed",
        full_name="Portal Owner",
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
    ws = SharedWorkspace(owner_id=ws_owner.id, name="Portal Test WS")
    db_session.add(ws)
    await db_session.commit()
    await db_session.refresh(ws)
    return ws


@pytest_asyncio.fixture
async def viewer_user(db_session: AsyncSession) -> User:
    user = User(
        email="portal_viewer@example.com",
        hashed_password="hashed",
        full_name="Portal Viewer",
        tier="professional",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def viewer_headers(viewer_user: User) -> dict:
    tokens = create_token_pair(viewer_user.id, viewer_user.email, viewer_user.tier)
    return {"Authorization": f"Bearer {tokens.access_token}"}


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
    await db_session.refresh(member)
    return member


@pytest_asyncio.fixture
async def approved_share(
    db_session: AsyncSession, test_workspace: SharedWorkspace
) -> SharedDataPermission:
    perm = SharedDataPermission(
        workspace_id=test_workspace.id,
        data_type=SharedDataType.RFP_SUMMARY,
        entity_id=1,
        requires_approval=False,
        approval_status=ShareApprovalStatus.APPROVED,
    )
    db_session.add(perm)
    await db_session.commit()
    await db_session.refresh(perm)
    return perm


class TestPartnerPortal:
    """Tests for GET /api/v1/collaboration/portal/{workspace_id}."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self, client: AsyncClient, test_workspace: SharedWorkspace
    ):
        response = await client.get(
            f"/api/v1/collaboration/portal/{test_workspace.id}",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_portal_as_owner(
        self,
        client: AsyncClient,
        ws_owner_headers: dict,
        test_workspace: SharedWorkspace,
        approved_share: SharedDataPermission,
    ):
        response = await client.get(
            f"/api/v1/collaboration/portal/{test_workspace.id}",
            headers=ws_owner_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["workspace_name"] == "Portal Test WS"
        assert isinstance(data["shared_items"], list)
        assert isinstance(data["members"], list)

    @pytest.mark.asyncio
    async def test_portal_as_viewer(
        self,
        client: AsyncClient,
        viewer_headers: dict,
        test_workspace: SharedWorkspace,
        viewer_membership: WorkspaceMember,
        approved_share: SharedDataPermission,
    ):
        response = await client.get(
            f"/api/v1/collaboration/portal/{test_workspace.id}",
            headers=viewer_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["shared_items"]) >= 1

    @pytest.mark.asyncio
    async def test_non_member_returns_403(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_workspace: SharedWorkspace,
    ):
        response = await client.get(
            f"/api/v1/collaboration/portal/{test_workspace.id}",
            headers=auth_headers,
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_portal_filters_pending_shares(
        self,
        client: AsyncClient,
        ws_owner_headers: dict,
        db_session: AsyncSession,
        test_workspace: SharedWorkspace,
    ):
        pending = SharedDataPermission(
            workspace_id=test_workspace.id,
            data_type=SharedDataType.FORECAST,
            entity_id=5,
            requires_approval=True,
            approval_status=ShareApprovalStatus.PENDING,
        )
        db_session.add(pending)
        await db_session.commit()

        response = await client.get(
            f"/api/v1/collaboration/portal/{test_workspace.id}",
            headers=ws_owner_headers,
        )
        assert response.status_code == 200
        statuses = [s["approval_status"] for s in response.json()["shared_items"]]
        assert "pending" not in statuses

    @pytest.mark.asyncio
    async def test_workspace_not_found(self, client: AsyncClient, ws_owner_headers: dict):
        response = await client.get(
            "/api/v1/collaboration/portal/99999",
            headers=ws_owner_headers,
        )
        assert response.status_code == 404
