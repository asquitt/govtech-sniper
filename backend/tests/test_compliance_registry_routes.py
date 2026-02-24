"""
Integration tests for compliance_registry.py routes:
  - GET  /api/v1/compliance-registry/controls
  - POST /api/v1/compliance-registry/controls
  - PATCH /api/v1/compliance-registry/controls/{control_id}
  - GET  /api/v1/compliance-registry/evidence
  - POST /api/v1/compliance-registry/evidence
  - POST /api/v1/compliance-registry/links
  - GET  /api/v1/compliance-registry/controls/{control_id}/evidence
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compliance_registry import (
    ComplianceControl,
    ComplianceEvidence,
    ControlFramework,
    ControlStatus,
    EvidenceType,
)
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def second_user(db_session: AsyncSession) -> User:
    user = User(
        email="registry-second@test.com",
        hashed_password=hash_password("Pass123!"),
        full_name="Registry Second",
        company_name="Other Co",
        tier="free",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def second_headers(second_user: User) -> dict:
    tokens = create_token_pair(second_user.id, second_user.email, second_user.tier)
    return {"Authorization": f"Bearer {tokens.access_token}"}


@pytest_asyncio.fixture
async def test_control(db_session: AsyncSession, test_user: User) -> ComplianceControl:
    control = ComplianceControl(
        user_id=test_user.id,
        framework=ControlFramework.NIST_800_171,
        control_id="AC-1",
        title="Access Control Policy",
        description="Establish access control policy",
        status=ControlStatus.IN_PROGRESS,
    )
    db_session.add(control)
    await db_session.commit()
    await db_session.refresh(control)
    return control


@pytest_asyncio.fixture
async def test_evidence(db_session: AsyncSession, test_user: User) -> ComplianceEvidence:
    evidence = ComplianceEvidence(
        user_id=test_user.id,
        title="Access Control Policy Doc",
        evidence_type=EvidenceType.POLICY,
        description="Official AC policy document",
    )
    db_session.add(evidence)
    await db_session.commit()
    await db_session.refresh(evidence)
    return evidence


# ---------------------------------------------------------------------------
# GET /api/v1/compliance-registry/controls
# ---------------------------------------------------------------------------


class TestListControls:
    """GET /api/v1/compliance-registry/controls"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/compliance-registry/controls")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_empty(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/compliance-registry/controls", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_returns_controls(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_control: ComplianceControl,
    ):
        response = await client.get("/api/v1/compliance-registry/controls", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["control_id"] == "AC-1"
        assert data[0]["framework"] == "nist_800_171"

    @pytest.mark.asyncio
    async def test_filter_by_framework(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_control: ComplianceControl,
    ):
        response = await client.get(
            "/api/v1/compliance-registry/controls?framework=nist_800_171",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert len(response.json()) == 1

    @pytest.mark.asyncio
    async def test_filter_by_status(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_control: ComplianceControl,
    ):
        response = await client.get(
            "/api/v1/compliance-registry/controls?status=in_progress",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert len(response.json()) == 1

    @pytest.mark.asyncio
    async def test_idor_isolation(
        self,
        client: AsyncClient,
        second_headers: dict,
        test_control: ComplianceControl,
    ):
        response = await client.get("/api/v1/compliance-registry/controls", headers=second_headers)
        assert response.status_code == 200
        assert len(response.json()) == 0


# ---------------------------------------------------------------------------
# POST /api/v1/compliance-registry/controls
# ---------------------------------------------------------------------------


class TestCreateControl:
    """POST /api/v1/compliance-registry/controls"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/compliance-registry/controls",
            json={
                "framework": "nist_800_171",
                "control_id": "AC-2",
                "title": "Account Management",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_control(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/compliance-registry/controls",
            headers=auth_headers,
            json={
                "framework": "nist_800_171",
                "control_id": "AC-2",
                "title": "Account Management",
                "description": "Manage system accounts",
                "status": "not_started",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["control_id"] == "AC-2"
        assert data["framework"] == "nist_800_171"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_missing_required(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/compliance-registry/controls",
            headers=auth_headers,
            json={"framework": "nist_800_171"},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# PATCH /api/v1/compliance-registry/controls/{control_id}
# ---------------------------------------------------------------------------


class TestUpdateControl:
    """PATCH /api/v1/compliance-registry/controls/{control_id}"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient, test_control: ComplianceControl):
        response = await client.patch(
            f"/api/v1/compliance-registry/controls/{test_control.id}",
            json={"status": "implemented"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_control(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_control: ComplianceControl,
    ):
        response = await client.patch(
            f"/api/v1/compliance-registry/controls/{test_control.id}",
            headers=auth_headers,
            json={"status": "implemented", "implementation_notes": "Done"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "implemented"
        assert data["implementation_notes"] == "Done"

    @pytest.mark.asyncio
    async def test_update_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.patch(
            "/api/v1/compliance-registry/controls/999999",
            headers=auth_headers,
            json={"status": "implemented"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_idor_update(
        self,
        client: AsyncClient,
        second_headers: dict,
        test_control: ComplianceControl,
    ):
        response = await client.patch(
            f"/api/v1/compliance-registry/controls/{test_control.id}",
            headers=second_headers,
            json={"status": "implemented"},
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/compliance-registry/evidence
# ---------------------------------------------------------------------------


class TestListEvidence:
    """GET /api/v1/compliance-registry/evidence"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/compliance-registry/evidence")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_evidence(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_evidence: ComplianceEvidence,
    ):
        response = await client.get("/api/v1/compliance-registry/evidence", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Access Control Policy Doc"

    @pytest.mark.asyncio
    async def test_filter_by_type(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_evidence: ComplianceEvidence,
    ):
        response = await client.get(
            "/api/v1/compliance-registry/evidence?evidence_type=policy",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert len(response.json()) == 1

    @pytest.mark.asyncio
    async def test_idor_isolation(
        self,
        client: AsyncClient,
        second_headers: dict,
        test_evidence: ComplianceEvidence,
    ):
        response = await client.get("/api/v1/compliance-registry/evidence", headers=second_headers)
        assert response.status_code == 200
        assert len(response.json()) == 0


# ---------------------------------------------------------------------------
# POST /api/v1/compliance-registry/evidence
# ---------------------------------------------------------------------------


class TestCreateEvidence:
    """POST /api/v1/compliance-registry/evidence"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/compliance-registry/evidence",
            json={"title": "Test", "evidence_type": "policy"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_evidence(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/compliance-registry/evidence",
            headers=auth_headers,
            json={
                "title": "New Evidence",
                "evidence_type": "screenshot",
                "description": "Screenshot of config",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Evidence"
        assert data["evidence_type"] == "screenshot"

    @pytest.mark.asyncio
    async def test_create_missing_required(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/compliance-registry/evidence",
            headers=auth_headers,
            json={"title": "Missing type"},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/compliance-registry/links
# ---------------------------------------------------------------------------


class TestLinkEvidenceToControl:
    """POST /api/v1/compliance-registry/links"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/compliance-registry/links",
            json={"control_id": 1, "evidence_id": 1},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_link_evidence(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_control: ComplianceControl,
        test_evidence: ComplianceEvidence,
    ):
        response = await client.post(
            "/api/v1/compliance-registry/links",
            headers=auth_headers,
            json={
                "control_id": test_control.id,
                "evidence_id": test_evidence.id,
                "notes": "Primary policy document",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "linked"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_link_nonexistent_control(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_evidence: ComplianceEvidence,
    ):
        response = await client.post(
            "/api/v1/compliance-registry/links",
            headers=auth_headers,
            json={"control_id": 999999, "evidence_id": test_evidence.id},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_link_nonexistent_evidence(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_control: ComplianceControl,
    ):
        response = await client.post(
            "/api/v1/compliance-registry/links",
            headers=auth_headers,
            json={"control_id": test_control.id, "evidence_id": 999999},
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/compliance-registry/controls/{control_id}/evidence
# ---------------------------------------------------------------------------


class TestGetControlEvidence:
    """GET /api/v1/compliance-registry/controls/{control_id}/evidence"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient, test_control: ComplianceControl):
        response = await client.get(
            f"/api/v1/compliance-registry/controls/{test_control.id}/evidence"
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_linked_evidence(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_control: ComplianceControl,
        test_evidence: ComplianceEvidence,
    ):
        # First link evidence
        await client.post(
            "/api/v1/compliance-registry/links",
            headers=auth_headers,
            json={
                "control_id": test_control.id,
                "evidence_id": test_evidence.id,
            },
        )

        response = await client.get(
            f"/api/v1/compliance-registry/controls/{test_control.id}/evidence",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Access Control Policy Doc"

    @pytest.mark.asyncio
    async def test_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(
            "/api/v1/compliance-registry/controls/999999/evidence",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_idor_control_evidence(
        self,
        client: AsyncClient,
        second_headers: dict,
        test_control: ComplianceControl,
    ):
        response = await client.get(
            f"/api/v1/compliance-registry/controls/{test_control.id}/evidence",
            headers=second_headers,
        )
        assert response.status_code == 404
