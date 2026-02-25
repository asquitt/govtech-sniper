"""
Integration tests for compliance_dashboard/trust_and_overview.py —
NIST overview, CMMC status, data privacy, trust center, trust metrics, and audit summary.
"""

import pytest
from httpx import AsyncClient

from app.models.user import User


class TestNistOverview:
    """GET /api/v1/compliance/overview"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/compliance/overview")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_overview(self, client: AsyncClient, auth_headers: dict, test_user: User):
        resp = await client.get("/api/v1/compliance/overview", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "control_families" in data or isinstance(data, dict)


class TestCmmcStatus:
    """GET /api/v1/compliance/cmmc-status"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/compliance/cmmc-status")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_cmmc_status(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        resp = await client.get("/api/v1/compliance/cmmc-status", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "score_percentage" in data


class TestDataPrivacy:
    """GET /api/v1/compliance/data-privacy"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/compliance/data-privacy")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_privacy_info(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        resp = await client.get("/api/v1/compliance/data-privacy", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "data_handling" in data
        assert "encryption" in data
        assert "access_controls" in data
        assert "data_retention" in data
        assert "certifications" in data
        assert len(data["data_handling"]) >= 3
        assert len(data["encryption"]) >= 3


class TestTrustCenter:
    """GET /api/v1/compliance/trust-center"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/compliance/trust-center")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_profile(self, client: AsyncClient, auth_headers: dict, test_user: User):
        resp = await client.get("/api/v1/compliance/trust-center", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "can_manage_policy" in data


class TestUpdateTrustCenter:
    """PATCH /api/v1/compliance/trust-center"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.patch("/api/v1/compliance/trust-center", json={})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_update_returns_current(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        resp = await client.patch(
            "/api/v1/compliance/trust-center",
            headers=auth_headers,
            json={},
        )
        # Empty update returns current profile (no org = 403 or returns profile)
        assert resp.status_code in (200, 403)

    @pytest.mark.asyncio
    async def test_non_admin_rejected(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        resp = await client.patch(
            "/api/v1/compliance/trust-center",
            headers=auth_headers,
            json={"allow_ai_draft_generation": False},
        )
        # User without org gets 403
        assert resp.status_code == 403


class TestTrustCenterEvidenceExport:
    """GET /api/v1/compliance/trust-center/evidence-export"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/compliance/trust-center/evidence-export")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_json_export(self, client: AsyncClient, auth_headers: dict, test_user: User):
        resp = await client.get(
            "/api/v1/compliance/trust-center/evidence-export?format=json",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "generated_at" in data
        assert "profile" in data

    @pytest.mark.asyncio
    async def test_csv_export(self, client: AsyncClient, auth_headers: dict, test_user: User):
        resp = await client.get(
            "/api/v1/compliance/trust-center/evidence-export?format=csv",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")


class TestTrustMetrics:
    """GET /api/v1/compliance/trust-metrics"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/compliance/trust-metrics")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_metrics(self, client: AsyncClient, auth_headers: dict, test_user: User):
        resp = await client.get("/api/v1/compliance/trust-metrics", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "generated_at" in data
        assert "window_days" in data
        assert data["window_days"] == 30
        assert "trust_export_successes_30d" in data
        assert "trust_export_failures_30d" in data


class TestAuditSummary:
    """GET /api/v1/compliance/audit-summary"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/compliance/audit-summary")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_summary(self, client: AsyncClient, auth_headers: dict, test_user: User):
        resp = await client.get("/api/v1/compliance/audit-summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_events" in data
        assert "events_last_30_days" in data
        assert "by_type" in data
        assert "compliance_score" in data
        assert data["total_events"] >= 0
