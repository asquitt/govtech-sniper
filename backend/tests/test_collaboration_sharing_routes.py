"""
Tests for collaboration/sharing routes - Data sharing, governance, and audit endpoints.
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
async def workspace_owner(db_session: AsyncSession) -> User:
    user = User(
        email="ws_owner@example.com",
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
async def owner_headers(workspace_owner: User) -> dict:
    tokens = create_token_pair(workspace_owner.id, workspace_owner.email, workspace_owner.tier)
    return {"Authorization": f"Bearer {tokens.access_token}"}


@pytest_asyncio.fixture
async def workspace_contributor(db_session: AsyncSession) -> User:
    user = User(
        email="ws_contributor@example.com",
        hashed_password="hashed",
        full_name="WS Contributor",
        tier="professional",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def contributor_headers(workspace_contributor: User) -> dict:
    tokens = create_token_pair(
        workspace_contributor.id, workspace_contributor.email, workspace_contributor.tier
    )
    return {"Authorization": f"Bearer {tokens.access_token}"}


@pytest_asyncio.fixture
async def workspace_viewer(db_session: AsyncSession) -> User:
    user = User(
        email="ws_viewer@example.com",
        hashed_password="hashed",
        full_name="WS Viewer",
        tier="professional",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def viewer_headers(workspace_viewer: User) -> dict:
    tokens = create_token_pair(workspace_viewer.id, workspace_viewer.email, workspace_viewer.tier)
    return {"Authorization": f"Bearer {tokens.access_token}"}


@pytest_asyncio.fixture
async def test_workspace(db_session: AsyncSession, workspace_owner: User) -> SharedWorkspace:
    ws = SharedWorkspace(
        owner_id=workspace_owner.id,
        name="Test Workspace",
        description="A workspace for testing",
    )
    db_session.add(ws)
    await db_session.commit()
    await db_session.refresh(ws)
    return ws


@pytest_asyncio.fixture
async def contributor_membership(
    db_session: AsyncSession,
    test_workspace: SharedWorkspace,
    workspace_contributor: User,
) -> WorkspaceMember:
    member = WorkspaceMember(
        workspace_id=test_workspace.id,
        user_id=workspace_contributor.id,
        role=WorkspaceRole.CONTRIBUTOR,
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(member)
    return member


@pytest_asyncio.fixture
async def viewer_membership(
    db_session: AsyncSession,
    test_workspace: SharedWorkspace,
    workspace_viewer: User,
) -> WorkspaceMember:
    member = WorkspaceMember(
        workspace_id=test_workspace.id,
        user_id=workspace_viewer.id,
        role=WorkspaceRole.VIEWER,
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(member)
    return member


@pytest_asyncio.fixture
async def admin_membership(
    db_session: AsyncSession,
    test_workspace: SharedWorkspace,
    workspace_contributor: User,
) -> WorkspaceMember:
    """Upgrade the contributor to admin for admin-level tests."""
    member = WorkspaceMember(
        workspace_id=test_workspace.id,
        user_id=workspace_contributor.id,
        role=WorkspaceRole.ADMIN,
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(member)
    return member


@pytest_asyncio.fixture
async def test_shared_permission(
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


@pytest_asyncio.fixture
async def pending_permission(
    db_session: AsyncSession, test_workspace: SharedWorkspace
) -> SharedDataPermission:
    perm = SharedDataPermission(
        workspace_id=test_workspace.id,
        data_type=SharedDataType.FORECAST,
        entity_id=2,
        requires_approval=True,
        approval_status=ShareApprovalStatus.PENDING,
    )
    db_session.add(perm)
    await db_session.commit()
    await db_session.refresh(perm)
    return perm


class TestContractFeedCatalog:
    """Tests for GET /api/v1/collaboration/contract-feeds/catalog."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        response = await client.get("/api/v1/collaboration/contract-feeds/catalog")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_catalog_returns_feeds(self, client: AsyncClient, owner_headers: dict):
        response = await client.get(
            "/api/v1/collaboration/contract-feeds/catalog",
            headers=owner_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert "id" in data[0]
        assert "name" in data[0]
        assert "source" in data[0]


class TestContractFeedPresets:
    """Tests for GET /api/v1/collaboration/contract-feeds/presets."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        response = await client.get("/api/v1/collaboration/contract-feeds/presets")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_presets_returns_list(self, client: AsyncClient, owner_headers: dict):
        response = await client.get(
            "/api/v1/collaboration/contract-feeds/presets",
            headers=owner_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert "key" in data[0]
        assert "feed_ids" in data[0]


class TestShareData:
    """Tests for POST /api/v1/collaboration/workspaces/{workspace_id}/share."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self, client: AsyncClient, test_workspace: SharedWorkspace
    ):
        response = await client.post(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/share",
            json={"data_type": "rfp_summary", "entity_id": 1},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_share_data_as_owner(
        self,
        client: AsyncClient,
        owner_headers: dict,
        test_workspace: SharedWorkspace,
    ):
        response = await client.post(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/share",
            headers=owner_headers,
            json={
                "data_type": "rfp_summary",
                "entity_id": 42,
                "requires_approval": False,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["data_type"] == "rfp_summary"
        assert data["entity_id"] == 42
        assert data["approval_status"] == "approved"

    @pytest.mark.asyncio
    async def test_share_data_as_contributor(
        self,
        client: AsyncClient,
        contributor_headers: dict,
        test_workspace: SharedWorkspace,
        contributor_membership: WorkspaceMember,
    ):
        response = await client.post(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/share",
            headers=contributor_headers,
            json={
                "data_type": "forecast",
                "entity_id": 10,
                "requires_approval": True,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["approval_status"] == "pending"
        assert data["requires_approval"] is True

    @pytest.mark.asyncio
    async def test_viewer_cannot_share(
        self,
        client: AsyncClient,
        viewer_headers: dict,
        test_workspace: SharedWorkspace,
        viewer_membership: WorkspaceMember,
    ):
        response = await client.post(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/share",
            headers=viewer_headers,
            json={"data_type": "rfp_summary", "entity_id": 1},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_non_member_cannot_share(
        self,
        client: AsyncClient,
        test_workspace: SharedWorkspace,
        auth_headers: dict,
    ):
        response = await client.post(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/share",
            headers=auth_headers,
            json={"data_type": "rfp_summary", "entity_id": 1},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_share_unknown_contract_feed_returns_400(
        self,
        client: AsyncClient,
        owner_headers: dict,
        test_workspace: SharedWorkspace,
    ):
        response = await client.post(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/share",
            headers=owner_headers,
            json={"data_type": "contract_feed", "entity_id": 99999},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_share_valid_contract_feed(
        self,
        client: AsyncClient,
        owner_headers: dict,
        test_workspace: SharedWorkspace,
    ):
        response = await client.post(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/share",
            headers=owner_headers,
            json={"data_type": "contract_feed", "entity_id": 1001},
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_workspace_not_found(self, client: AsyncClient, owner_headers: dict):
        response = await client.post(
            "/api/v1/collaboration/workspaces/99999/share",
            headers=owner_headers,
            json={"data_type": "rfp_summary", "entity_id": 1},
        )
        assert response.status_code == 404


class TestApplyContractFeedPreset:
    """Tests for POST /api/v1/collaboration/workspaces/{workspace_id}/share/preset."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self, client: AsyncClient, test_workspace: SharedWorkspace
    ):
        response = await client.post(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/share/preset",
            json={"preset_key": "federal_core"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_apply_preset_success(
        self,
        client: AsyncClient,
        owner_headers: dict,
        test_workspace: SharedWorkspace,
    ):
        response = await client.post(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/share/preset",
            headers=owner_headers,
            json={"preset_key": "federal_core"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["preset_key"] == "federal_core"
        assert data["applied_count"] == 3
        assert len(data["shared_items"]) == 3

    @pytest.mark.asyncio
    async def test_apply_preset_skips_existing(
        self,
        client: AsyncClient,
        owner_headers: dict,
        test_workspace: SharedWorkspace,
    ):
        # Apply once
        await client.post(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/share/preset",
            headers=owner_headers,
            json={"preset_key": "federal_core"},
        )
        # Apply again — should skip all existing
        response = await client.post(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/share/preset",
            headers=owner_headers,
            json={"preset_key": "federal_core"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["applied_count"] == 0

    @pytest.mark.asyncio
    async def test_apply_unknown_preset_returns_404(
        self,
        client: AsyncClient,
        owner_headers: dict,
        test_workspace: SharedWorkspace,
    ):
        response = await client.post(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/share/preset",
            headers=owner_headers,
            json={"preset_key": "nonexistent_preset"},
        )
        assert response.status_code == 404


class TestListSharedData:
    """Tests for GET /api/v1/collaboration/workspaces/{workspace_id}/shared."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self, client: AsyncClient, test_workspace: SharedWorkspace
    ):
        response = await client.get(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/shared",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_shared_data_as_owner(
        self,
        client: AsyncClient,
        owner_headers: dict,
        test_workspace: SharedWorkspace,
        test_shared_permission: SharedDataPermission,
    ):
        response = await client.get(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/shared",
            headers=owner_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["data_type"] == "rfp_summary"

    @pytest.mark.asyncio
    async def test_list_shared_as_viewer(
        self,
        client: AsyncClient,
        viewer_headers: dict,
        test_workspace: SharedWorkspace,
        viewer_membership: WorkspaceMember,
        test_shared_permission: SharedDataPermission,
    ):
        response = await client.get(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/shared",
            headers=viewer_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_non_member_returns_403(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_workspace: SharedWorkspace,
    ):
        response = await client.get(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/shared",
            headers=auth_headers,
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_empty_shared_data(
        self,
        client: AsyncClient,
        owner_headers: dict,
        test_workspace: SharedWorkspace,
    ):
        response = await client.get(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/shared",
            headers=owner_headers,
        )
        assert response.status_code == 200
        assert response.json() == []


class TestGovernanceSummary:
    """Tests for GET /api/v1/collaboration/workspaces/{workspace_id}/shared/governance-summary."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self, client: AsyncClient, test_workspace: SharedWorkspace
    ):
        response = await client.get(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/shared/governance-summary",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_governance_summary_success(
        self,
        client: AsyncClient,
        owner_headers: dict,
        test_workspace: SharedWorkspace,
        test_shared_permission: SharedDataPermission,
        pending_permission: SharedDataPermission,
    ):
        response = await client.get(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/shared/governance-summary",
            headers=owner_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["workspace_id"] == test_workspace.id
        assert data["total_shared_items"] == 2
        assert data["approved_count"] >= 1
        assert data["pending_approval_count"] >= 1


class TestGovernanceTrends:
    """Tests for GET /api/v1/collaboration/workspaces/{workspace_id}/shared/governance-trends."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self, client: AsyncClient, test_workspace: SharedWorkspace
    ):
        response = await client.get(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/shared/governance-trends",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_governance_trends_success(
        self,
        client: AsyncClient,
        owner_headers: dict,
        test_workspace: SharedWorkspace,
        test_shared_permission: SharedDataPermission,
    ):
        response = await client.get(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/shared/governance-trends",
            headers=owner_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["workspace_id"] == test_workspace.id
        assert data["days"] == 30
        assert data["sla_hours"] == 24
        assert "points" in data
        assert "sla_approval_rate" in data

    @pytest.mark.asyncio
    async def test_governance_trends_custom_params(
        self,
        client: AsyncClient,
        owner_headers: dict,
        test_workspace: SharedWorkspace,
    ):
        response = await client.get(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/shared/governance-trends",
            headers=owner_headers,
            params={"days": 7, "sla_hours": 48},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["days"] == 7
        assert data["sla_hours"] == 48


class TestGovernanceAnomalies:
    """Tests for GET /api/v1/collaboration/workspaces/{workspace_id}/shared/governance-anomalies."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self, client: AsyncClient, test_workspace: SharedWorkspace
    ):
        response = await client.get(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/shared/governance-anomalies",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_anomalies_healthy_workspace(
        self,
        client: AsyncClient,
        owner_headers: dict,
        test_workspace: SharedWorkspace,
    ):
        response = await client.get(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/shared/governance-anomalies",
            headers=owner_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        # Empty workspace with 0 approved items triggers low_sla_rate (0% < 80%)
        codes = [a["code"] for a in data]
        assert "low_sla_rate" in codes or "healthy" in codes

    @pytest.mark.asyncio
    async def test_anomalies_with_pending(
        self,
        client: AsyncClient,
        owner_headers: dict,
        test_workspace: SharedWorkspace,
        pending_permission: SharedDataPermission,
    ):
        response = await client.get(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/shared/governance-anomalies",
            headers=owner_headers,
        )
        assert response.status_code == 200
        data = response.json()
        codes = [a["code"] for a in data]
        assert "pending_approvals" in codes


class TestAuditExport:
    """Tests for GET /api/v1/collaboration/workspaces/{workspace_id}/shared/audit-export."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self, client: AsyncClient, test_workspace: SharedWorkspace
    ):
        response = await client.get(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/shared/audit-export",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_audit_export_as_owner(
        self,
        client: AsyncClient,
        owner_headers: dict,
        test_workspace: SharedWorkspace,
        test_shared_permission: SharedDataPermission,
    ):
        response = await client.get(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/shared/audit-export",
            headers=owner_headers,
        )
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "attachment" in response.headers.get("content-disposition", "")

    @pytest.mark.asyncio
    async def test_audit_export_viewer_forbidden(
        self,
        client: AsyncClient,
        viewer_headers: dict,
        test_workspace: SharedWorkspace,
        viewer_membership: WorkspaceMember,
    ):
        response = await client.get(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/shared/audit-export",
            headers=viewer_headers,
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_audit_export_contributor_forbidden(
        self,
        client: AsyncClient,
        contributor_headers: dict,
        test_workspace: SharedWorkspace,
        contributor_membership: WorkspaceMember,
    ):
        response = await client.get(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/shared/audit-export",
            headers=contributor_headers,
        )
        assert response.status_code == 403


class TestApproveSharedData:
    """Tests for POST /api/v1/collaboration/workspaces/{workspace_id}/shared/{perm_id}/approve."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self,
        client: AsyncClient,
        test_workspace: SharedWorkspace,
        pending_permission: SharedDataPermission,
    ):
        response = await client.post(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/shared/{pending_permission.id}/approve",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_approve_as_owner(
        self,
        client: AsyncClient,
        owner_headers: dict,
        test_workspace: SharedWorkspace,
        pending_permission: SharedDataPermission,
    ):
        response = await client.post(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/shared/{pending_permission.id}/approve",
            headers=owner_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["approval_status"] == "approved"

    @pytest.mark.asyncio
    async def test_approve_as_admin(
        self,
        client: AsyncClient,
        contributor_headers: dict,
        test_workspace: SharedWorkspace,
        admin_membership: WorkspaceMember,
        pending_permission: SharedDataPermission,
    ):
        response = await client.post(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/shared/{pending_permission.id}/approve",
            headers=contributor_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_viewer_cannot_approve(
        self,
        client: AsyncClient,
        viewer_headers: dict,
        test_workspace: SharedWorkspace,
        viewer_membership: WorkspaceMember,
        pending_permission: SharedDataPermission,
    ):
        response = await client.post(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/shared/{pending_permission.id}/approve",
            headers=viewer_headers,
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_approve_nonexistent_returns_404(
        self,
        client: AsyncClient,
        owner_headers: dict,
        test_workspace: SharedWorkspace,
    ):
        response = await client.post(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/shared/99999/approve",
            headers=owner_headers,
        )
        assert response.status_code == 404


class TestUnshareData:
    """Tests for DELETE /api/v1/collaboration/workspaces/{workspace_id}/shared/{perm_id}."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self,
        client: AsyncClient,
        test_workspace: SharedWorkspace,
        test_shared_permission: SharedDataPermission,
    ):
        response = await client.delete(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/shared/{test_shared_permission.id}",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_unshare_as_owner(
        self,
        client: AsyncClient,
        owner_headers: dict,
        test_workspace: SharedWorkspace,
        test_shared_permission: SharedDataPermission,
    ):
        response = await client.delete(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/shared/{test_shared_permission.id}",
            headers=owner_headers,
        )
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_unshare_as_contributor(
        self,
        client: AsyncClient,
        contributor_headers: dict,
        test_workspace: SharedWorkspace,
        contributor_membership: WorkspaceMember,
        test_shared_permission: SharedDataPermission,
    ):
        response = await client.delete(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/shared/{test_shared_permission.id}",
            headers=contributor_headers,
        )
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_viewer_cannot_unshare(
        self,
        client: AsyncClient,
        viewer_headers: dict,
        test_workspace: SharedWorkspace,
        viewer_membership: WorkspaceMember,
        test_shared_permission: SharedDataPermission,
    ):
        response = await client.delete(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/shared/{test_shared_permission.id}",
            headers=viewer_headers,
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_unshare_nonexistent_returns_404(
        self,
        client: AsyncClient,
        owner_headers: dict,
        test_workspace: SharedWorkspace,
    ):
        response = await client.delete(
            f"/api/v1/collaboration/workspaces/{test_workspace.id}/shared/99999",
            headers=owner_headers,
        )
        assert response.status_code == 404
