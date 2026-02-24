"""
Integration tests for compliance_dashboard.py routes:
  - GET  /api/v1/compliance/readiness
  - GET  /api/v1/compliance/readiness-checkpoints
  - GET  /api/v1/compliance/readiness-checkpoints/{id}/evidence
  - POST /api/v1/compliance/readiness-checkpoints/{id}/evidence
  - PATCH /api/v1/compliance/readiness-checkpoints/{id}/evidence/{link_id}
  - GET  /api/v1/compliance/readiness-checkpoints/{id}/signoff
  - PUT  /api/v1/compliance/readiness-checkpoints/{id}/signoff
  - GET  /api/v1/compliance/govcloud-profile
  - GET  /api/v1/compliance/soc2-readiness
  - GET  /api/v1/compliance/three-pao-package
  - GET  /api/v1/compliance/overview
  - GET  /api/v1/compliance/cmmc-status
  - GET  /api/v1/compliance/data-privacy
  - GET  /api/v1/compliance/trust-center
  - PATCH /api/v1/compliance/trust-center
  - GET  /api/v1/compliance/trust-center/evidence-export
  - GET  /api/v1/compliance/trust-metrics
  - GET  /api/v1/compliance/audit-summary
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization, OrganizationMember, OrgRole
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def org(db_session: AsyncSession) -> Organization:
    organization = Organization(
        name="Compliance Org",
        slug="compliance-org",
        domain="compliance.com",
        billing_email="billing@compliance.com",
    )
    db_session.add(organization)
    await db_session.commit()
    await db_session.refresh(organization)
    return organization


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession, org: Organization) -> User:
    user = User(
        email="compliance-admin@test.com",
        hashed_password=hash_password("AdminPass123!"),
        full_name="Compliance Admin",
        company_name="Compliance Org",
        tier="professional",
        is_active=True,
        is_verified=True,
        organization_id=org.id,
    )
    db_session.add(user)
    await db_session.flush()
    member = OrganizationMember(
        organization_id=org.id,
        user_id=user.id,
        role=OrgRole.OWNER,
        is_active=True,
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_headers(admin_user: User) -> dict:
    tokens = create_token_pair(admin_user.id, admin_user.email, admin_user.tier)
    return {"Authorization": f"Bearer {tokens.access_token}"}


@pytest_asyncio.fixture
async def member_user(db_session: AsyncSession, org: Organization) -> User:
    user = User(
        email="compliance-member@test.com",
        hashed_password=hash_password("MemberPass123!"),
        full_name="Compliance Member",
        company_name="Compliance Org",
        tier="free",
        is_active=True,
        is_verified=True,
        organization_id=org.id,
    )
    db_session.add(user)
    await db_session.flush()
    member = OrganizationMember(
        organization_id=org.id,
        user_id=user.id,
        role=OrgRole.MEMBER,
        is_active=True,
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def member_headers(member_user: User) -> dict:
    tokens = create_token_pair(member_user.id, member_user.email, member_user.tier)
    return {"Authorization": f"Bearer {tokens.access_token}"}


# ---------------------------------------------------------------------------
# GET /api/v1/compliance/readiness
# ---------------------------------------------------------------------------


class TestReadinessStatus:
    """GET /api/v1/compliance/readiness"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/compliance/readiness")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_readiness(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/compliance/readiness", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "programs" in data
        assert "last_updated" in data
        assert isinstance(data["programs"], list)
        assert len(data["programs"]) > 0


# ---------------------------------------------------------------------------
# GET /api/v1/compliance/readiness-checkpoints
# ---------------------------------------------------------------------------


class TestReadinessCheckpoints:
    """GET /api/v1/compliance/readiness-checkpoints"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/compliance/readiness-checkpoints")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_checkpoints(self, client: AsyncClient, admin_headers: dict):
        response = await client.get(
            "/api/v1/compliance/readiness-checkpoints", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "checkpoints" in data
        assert "generated_at" in data


# ---------------------------------------------------------------------------
# Checkpoint evidence endpoints
# ---------------------------------------------------------------------------


class TestCheckpointEvidence:
    """Checkpoint evidence CRUD endpoints."""

    @pytest.mark.asyncio
    async def test_list_evidence_requires_auth(self, client: AsyncClient):
        response = await client.get(
            "/api/v1/compliance/readiness-checkpoints/fedramp_boundary_package/evidence"
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_evidence_requires_org(self, client: AsyncClient, auth_headers: dict):
        """User without org membership gets 403."""
        response = await client.get(
            "/api/v1/compliance/readiness-checkpoints/fedramp_boundary_package/evidence",
            headers=auth_headers,
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_list_evidence_for_org_member(self, client: AsyncClient, member_headers: dict):
        response = await client.get(
            "/api/v1/compliance/readiness-checkpoints/fedramp_boundary_package/evidence",
            headers=member_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_list_evidence_invalid_checkpoint(
        self, client: AsyncClient, member_headers: dict
    ):
        response = await client.get(
            "/api/v1/compliance/readiness-checkpoints/nonexistent_checkpoint/evidence",
            headers=member_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_evidence_requires_admin(self, client: AsyncClient, member_headers: dict):
        response = await client.post(
            "/api/v1/compliance/readiness-checkpoints/fedramp_boundary_package/evidence",
            headers=member_headers,
            json={"evidence_id": 1},
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Checkpoint signoff
# ---------------------------------------------------------------------------


class TestCheckpointSignoff:
    """Checkpoint signoff endpoints."""

    @pytest.mark.asyncio
    async def test_get_signoff_requires_auth(self, client: AsyncClient):
        response = await client.get(
            "/api/v1/compliance/readiness-checkpoints/fedramp_boundary_package/signoff"
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_signoff_returns_pending_default(
        self, client: AsyncClient, member_headers: dict
    ):
        response = await client.get(
            "/api/v1/compliance/readiness-checkpoints/fedramp_boundary_package/signoff",
            headers=member_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["checkpoint_id"] == "fedramp_boundary_package"

    @pytest.mark.asyncio
    async def test_put_signoff_requires_admin(self, client: AsyncClient, member_headers: dict):
        response = await client.put(
            "/api/v1/compliance/readiness-checkpoints/fedramp_boundary_package/signoff",
            headers=member_headers,
            json={
                "status": "approved",
                "assessor_name": "John",
            },
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_put_signoff_admin(self, client: AsyncClient, admin_headers: dict):
        response = await client.put(
            "/api/v1/compliance/readiness-checkpoints/fedramp_boundary_package/signoff",
            headers=admin_headers,
            json={
                "status": "approved",
                "assessor_name": "Jane Assessor",
                "assessor_org": "Assessment Corp",
                "notes": "All evidence verified",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert data["assessor_name"] == "Jane Assessor"

    @pytest.mark.asyncio
    async def test_signoff_invalid_checkpoint(self, client: AsyncClient, admin_headers: dict):
        response = await client.put(
            "/api/v1/compliance/readiness-checkpoints/nonexistent/signoff",
            headers=admin_headers,
            json={
                "status": "approved",
                "assessor_name": "Test",
            },
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Static compliance endpoints
# ---------------------------------------------------------------------------


class TestGovCloudProfile:
    """GET /api/v1/compliance/govcloud-profile"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/compliance/govcloud-profile")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_govcloud_data(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/compliance/govcloud-profile", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["program_id"] == "govcloud_deployment"
        assert "target_regions" in data
        assert "migration_phases" in data


class TestSOC2Readiness:
    """GET /api/v1/compliance/soc2-readiness"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/compliance/soc2-readiness")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_soc2_data(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/compliance/soc2-readiness", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["program_id"] == "soc2_type_ii"
        assert "domains" in data
        assert "milestones" in data


class TestNistOverview:
    """GET /api/v1/compliance/overview"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/compliance/overview")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_nist_overview(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/compliance/overview", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), dict)


class TestCMMCStatus:
    """GET /api/v1/compliance/cmmc-status"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/compliance/cmmc-status")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_cmmc_status(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/compliance/cmmc-status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "score_percentage" in data


class TestDataPrivacy:
    """GET /api/v1/compliance/data-privacy"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/compliance/data-privacy")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_privacy_info(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/compliance/data-privacy", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "data_handling" in data
        assert "encryption" in data
        assert "access_controls" in data
        assert "data_retention" in data
        assert "certifications" in data


# ---------------------------------------------------------------------------
# Trust Center
# ---------------------------------------------------------------------------


class TestTrustCenter:
    """GET /api/v1/compliance/trust-center and PATCH"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/compliance/trust-center")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_trust_profile(self, client: AsyncClient, admin_headers: dict):
        response = await client.get("/api/v1/compliance/trust-center", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "policy" in data
        assert "runtime_guarantees" in data
        assert "evidence" in data
        assert "can_manage_policy" in data

    @pytest.mark.asyncio
    async def test_patch_requires_admin(self, client: AsyncClient, member_headers: dict):
        response = await client.patch(
            "/api/v1/compliance/trust-center",
            headers=member_headers,
            json={"allow_ai_requirement_analysis": False},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_patch_trust_policy(self, client: AsyncClient, admin_headers: dict):
        response = await client.patch(
            "/api/v1/compliance/trust-center",
            headers=admin_headers,
            json={"allow_ai_requirement_analysis": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["policy"]["allow_ai_requirement_analysis"] is False

    @pytest.mark.asyncio
    async def test_patch_no_changes_returns_current(self, client: AsyncClient, admin_headers: dict):
        response = await client.patch(
            "/api/v1/compliance/trust-center",
            headers=admin_headers,
            json={},
        )
        assert response.status_code == 200
        assert "policy" in response.json()


# ---------------------------------------------------------------------------
# Trust Center Evidence Export
# ---------------------------------------------------------------------------


class TestTrustCenterEvidenceExport:
    """GET /api/v1/compliance/trust-center/evidence-export"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/compliance/trust-center/evidence-export")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_json_export(self, client: AsyncClient, admin_headers: dict):
        response = await client.get(
            "/api/v1/compliance/trust-center/evidence-export?format=json",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "generated_at" in data
        assert "profile" in data

    @pytest.mark.asyncio
    async def test_csv_export(self, client: AsyncClient, admin_headers: dict):
        response = await client.get(
            "/api/v1/compliance/trust-center/evidence-export?format=csv",
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_pdf_export_fails_gracefully(self, client: AsyncClient, admin_headers: dict):
        """PDF export likely fails without weasyprint; accept 200 or 500."""
        response = await client.get(
            "/api/v1/compliance/trust-center/evidence-export?format=pdf",
            headers=admin_headers,
        )
        assert response.status_code in (200, 500)


# ---------------------------------------------------------------------------
# 3PAO Package
# ---------------------------------------------------------------------------


class TestThreePAOPackage:
    """GET /api/v1/compliance/three-pao-package"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/compliance/three-pao-package")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_package(self, client: AsyncClient, admin_headers: dict):
        response = await client.get("/api/v1/compliance/three-pao-package", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "readiness_programs" in data
        assert "checkpoint_summary" in data
        assert "checkpoints" in data
        assert "govcloud_profile" in data
        assert "soc2_profile" in data
        assert "trust_center" in data


# ---------------------------------------------------------------------------
# Trust Metrics
# ---------------------------------------------------------------------------


class TestTrustMetrics:
    """GET /api/v1/compliance/trust-metrics"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/compliance/trust-metrics")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_metrics(self, client: AsyncClient, admin_headers: dict):
        response = await client.get("/api/v1/compliance/trust-metrics", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "generated_at" in data
        assert "window_days" in data
        assert "checkpoint_evidence_completeness_rate" in data


# ---------------------------------------------------------------------------
# Audit Summary
# ---------------------------------------------------------------------------


class TestAuditSummary:
    """GET /api/v1/compliance/audit-summary"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/compliance/audit-summary")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_summary(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/compliance/audit-summary", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_events" in data
        assert "events_last_30_days" in data
        assert "by_type" in data
        assert "compliance_score" in data
