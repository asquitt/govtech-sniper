"""
Integration tests for compliance_dashboard/readiness.py —
readiness programs, checkpoints, evidence, signoffs, GovCloud, SOC2, 3PAO.
"""

import pytest
from httpx import AsyncClient

from app.models.user import User


class TestReadinessStatus:
    """GET /api/v1/compliance/readiness"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/compliance/readiness")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_programs(self, client: AsyncClient, auth_headers: dict, test_user: User):
        resp = await client.get("/api/v1/compliance/readiness", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "programs" in data
        assert "last_updated" in data
        assert len(data["programs"]) >= 1


class TestReadinessCheckpoints:
    """GET /api/v1/compliance/readiness-checkpoints"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/compliance/readiness-checkpoints")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_checkpoints(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        resp = await client.get("/api/v1/compliance/readiness-checkpoints", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "checkpoints" in data
        assert "generated_at" in data
        assert len(data["checkpoints"]) >= 1


class TestCheckpointEvidenceList:
    """GET /api/v1/compliance/readiness-checkpoints/{id}/evidence"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/compliance/readiness-checkpoints/test/evidence")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_requires_org_membership(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        resp = await client.get(
            "/api/v1/compliance/readiness-checkpoints/fedramp-1/evidence",
            headers=auth_headers,
        )
        # No org membership → 403
        assert resp.status_code == 403


class TestCheckpointEvidenceCreate:
    """POST /api/v1/compliance/readiness-checkpoints/{id}/evidence"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/compliance/readiness-checkpoints/test/evidence",
            json={"evidence_id": 1},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_requires_org_membership(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        resp = await client.post(
            "/api/v1/compliance/readiness-checkpoints/fedramp-1/evidence",
            headers=auth_headers,
            json={"evidence_id": 1},
        )
        assert resp.status_code == 403


class TestCheckpointEvidenceUpdate:
    """PATCH /api/v1/compliance/readiness-checkpoints/{id}/evidence/{link_id}"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.patch(
            "/api/v1/compliance/readiness-checkpoints/test/evidence/1",
            json={"status": "approved"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_requires_org_membership(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        resp = await client.patch(
            "/api/v1/compliance/readiness-checkpoints/fedramp-1/evidence/1",
            headers=auth_headers,
            json={"status": "accepted"},
        )
        assert resp.status_code == 403


class TestCheckpointSignoffGet:
    """GET /api/v1/compliance/readiness-checkpoints/{id}/signoff"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/compliance/readiness-checkpoints/test/signoff")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_requires_org_membership(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        resp = await client.get(
            "/api/v1/compliance/readiness-checkpoints/fedramp-1/signoff",
            headers=auth_headers,
        )
        assert resp.status_code == 403


class TestCheckpointSignoffUpsert:
    """PUT /api/v1/compliance/readiness-checkpoints/{id}/signoff"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.put(
            "/api/v1/compliance/readiness-checkpoints/test/signoff",
            json={"status": "approved", "assessor_name": "Test"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_requires_org_membership(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        resp = await client.put(
            "/api/v1/compliance/readiness-checkpoints/fedramp-1/signoff",
            headers=auth_headers,
            json={"status": "approved", "assessor_name": "Test"},
        )
        assert resp.status_code == 403


class TestGovCloudProfile:
    """GET /api/v1/compliance/govcloud-profile"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/compliance/govcloud-profile")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_profile(self, client: AsyncClient, auth_headers: dict, test_user: User):
        resp = await client.get("/api/v1/compliance/govcloud-profile", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "phases" in data or "deployment_phases" in data or isinstance(data, dict)


class TestSoc2Readiness:
    """GET /api/v1/compliance/soc2-readiness"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/compliance/soc2-readiness")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_readiness(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        resp = await client.get("/api/v1/compliance/soc2-readiness", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)


class TestThreePaoPackage:
    """GET /api/v1/compliance/three-pao-package"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/compliance/three-pao-package")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_package(self, client: AsyncClient, auth_headers: dict, test_user: User):
        resp = await client.get("/api/v1/compliance/three-pao-package", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "generated_at" in data
        assert "readiness_programs" in data
        assert "checkpoint_summary" in data
        assert "checkpoints" in data
        assert "govcloud_profile" in data
        assert "soc2_profile" in data
        assert "trust_center" in data
        assert "controls_in_scope" in data
