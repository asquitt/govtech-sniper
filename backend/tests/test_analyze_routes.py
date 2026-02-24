"""
Integration tests for analyze.py:
  - POST /api/v1/analyze/{rfp_id}           (trigger analysis)
  - GET  /api/v1/analyze/{rfp_id}/status/{task_id}  (check status)
  - GET  /api/v1/analyze/{rfp_id}/matrix     (get compliance matrix)
  - GET  /api/v1/analyze/{rfp_id}/gaps       (get compliance gaps)
  - POST /api/v1/analyze/{rfp_id}/matrix     (add requirement)
  - PATCH /api/v1/analyze/{rfp_id}/matrix/{requirement_id}  (update requirement)
  - DELETE /api/v1/analyze/{rfp_id}/matrix/{requirement_id} (delete requirement)
  - POST /api/v1/analyze/{rfp_id}/filter     (trigger killer filter)
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rfp import RFP, ComplianceMatrix, RFPStatus
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password


@pytest_asyncio.fixture
async def test_matrix(db_session: AsyncSession, test_rfp: RFP) -> ComplianceMatrix:
    """Create a compliance matrix with two requirements for testing."""
    matrix = ComplianceMatrix(
        rfp_id=test_rfp.id,
        requirements=[
            {
                "id": "REQ-001",
                "section": "L.1",
                "requirement_text": "Technical approach",
                "importance": "mandatory",
                "is_addressed": False,
                "category": None,
                "page_reference": None,
                "keywords": [],
                "notes": None,
            },
            {
                "id": "REQ-002",
                "section": "L.2",
                "requirement_text": "Past perf",
                "importance": "evaluated",
                "is_addressed": True,
                "status": "addressed",
                "category": None,
                "page_reference": None,
                "keywords": [],
                "notes": None,
            },
        ],
        total_requirements=2,
        mandatory_count=1,
        addressed_count=1,
    )
    db_session.add(matrix)
    await db_session.commit()
    await db_session.refresh(matrix)
    return matrix


@pytest_asyncio.fixture
async def other_user_headers(db_session: AsyncSession) -> dict:
    """Create a second user and return auth headers for IDOR tests."""
    other = User(
        email="other@example.com",
        hashed_password=hash_password("OtherPass123!"),
        full_name="Other User",
        company_name="Other Co",
        tier="free",
        is_active=True,
        is_verified=True,
    )
    db_session.add(other)
    await db_session.commit()
    await db_session.refresh(other)
    tokens = create_token_pair(other.id, other.email, other.tier)
    return {"Authorization": f"Bearer {tokens.access_token}"}


# ---------------------------------------------------------------------------
# POST /api/v1/analyze/{rfp_id} — Trigger analysis
# ---------------------------------------------------------------------------


class TestTriggerAnalysis:
    """Tests for POST /api/v1/analyze/{rfp_id}."""

    @pytest.mark.asyncio
    async def test_trigger_requires_auth(self, client: AsyncClient, test_rfp: RFP):
        """Returns 401 without auth token."""
        resp = await client.post(f"/api/v1/analyze/{test_rfp.id}")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_trigger_idor(self, client: AsyncClient, other_user_headers: dict, test_rfp: RFP):
        """Another user's RFP returns 404."""
        resp = await client.post(f"/api/v1/analyze/{test_rfp.id}", headers=other_user_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_trigger_rfp_not_found(self, client: AsyncClient, auth_headers: dict):
        """Non-existent RFP returns 404."""
        resp = await client.post("/api/v1/analyze/999999", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_trigger_rfp_no_content_returns_400(
        self, client: AsyncClient, auth_headers: dict, test_rfp: RFP
    ):
        """RFP with no full_text or description returns 400."""
        # test_rfp has no full_text and no description by default
        resp = await client.post(f"/api/v1/analyze/{test_rfp.id}", headers=auth_headers)
        assert resp.status_code == 400
        assert "no text content" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_trigger_already_analyzed(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
        db_session: AsyncSession,
    ):
        """Already-analyzed RFP returns status already_completed."""
        test_rfp.status = RFPStatus.ANALYZED
        test_rfp.full_text = "Some content"
        db_session.add(test_rfp)
        await db_session.commit()

        resp = await client.post(f"/api/v1/analyze/{test_rfp.id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "already_completed"
        assert data["task_id"] == "none"


# ---------------------------------------------------------------------------
# GET /api/v1/analyze/{rfp_id}/status/{task_id} — Check status
# ---------------------------------------------------------------------------


class TestAnalysisStatus:
    """Tests for GET /api/v1/analyze/{rfp_id}/status/{task_id}."""

    @pytest.mark.asyncio
    async def test_status_requires_auth(self, client: AsyncClient, test_rfp: RFP):
        """Returns 401 without auth token."""
        resp = await client.get(f"/api/v1/analyze/{test_rfp.id}/status/fake-task-id")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_status_idor(self, client: AsyncClient, other_user_headers: dict, test_rfp: RFP):
        """Another user cannot check status of first user's RFP."""
        resp = await client.get(
            f"/api/v1/analyze/{test_rfp.id}/status/fake-task-id",
            headers=other_user_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_status_rfp_not_found(self, client: AsyncClient, auth_headers: dict):
        """Non-existent RFP returns 404."""
        resp = await client.get("/api/v1/analyze/999999/status/fake-task-id", headers=auth_headers)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/analyze/{rfp_id}/matrix — Get compliance matrix
# ---------------------------------------------------------------------------


class TestGetComplianceMatrix:
    """Tests for GET /api/v1/analyze/{rfp_id}/matrix."""

    @pytest.mark.asyncio
    async def test_matrix_requires_auth(self, client: AsyncClient, test_rfp: RFP):
        """Returns 401 without auth token."""
        resp = await client.get(f"/api/v1/analyze/{test_rfp.id}/matrix")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_matrix_idor(self, client: AsyncClient, other_user_headers: dict, test_rfp: RFP):
        """Another user's RFP matrix returns 404."""
        resp = await client.get(f"/api/v1/analyze/{test_rfp.id}/matrix", headers=other_user_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_matrix_empty_when_no_matrix(
        self, client: AsyncClient, auth_headers: dict, test_rfp: RFP
    ):
        """Returns an empty matrix shape when no matrix exists yet."""
        resp = await client.get(f"/api/v1/analyze/{test_rfp.id}/matrix", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 0
        assert data["requirements"] == []
        assert data["total_requirements"] == 0

    @pytest.mark.asyncio
    async def test_matrix_returns_requirements(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
        test_matrix: ComplianceMatrix,
    ):
        """Returns matrix with all requirements."""
        resp = await client.get(f"/api/v1/analyze/{test_rfp.id}/matrix", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_requirements"] == 2
        assert data["mandatory_count"] == 1
        assert data["addressed_count"] == 1
        assert len(data["requirements"]) == 2
        req_ids = {r["id"] for r in data["requirements"]}
        assert req_ids == {"REQ-001", "REQ-002"}


# ---------------------------------------------------------------------------
# GET /api/v1/analyze/{rfp_id}/gaps — Get compliance gaps
# ---------------------------------------------------------------------------


class TestGetComplianceGaps:
    """Tests for GET /api/v1/analyze/{rfp_id}/gaps."""

    @pytest.mark.asyncio
    async def test_gaps_requires_auth(self, client: AsyncClient, test_rfp: RFP):
        """Returns 401 without auth token."""
        resp = await client.get(f"/api/v1/analyze/{test_rfp.id}/gaps")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_gaps_idor(self, client: AsyncClient, other_user_headers: dict, test_rfp: RFP):
        """Another user's RFP gaps returns 404."""
        resp = await client.get(f"/api/v1/analyze/{test_rfp.id}/gaps", headers=other_user_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_gaps_no_matrix_returns_404(
        self, client: AsyncClient, auth_headers: dict, test_rfp: RFP
    ):
        """Returns 404 when no compliance matrix exists."""
        resp = await client.get(f"/api/v1/analyze/{test_rfp.id}/gaps", headers=auth_headers)
        assert resp.status_code == 404
        assert "Run analysis first" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_gaps_returns_unaddressed_only(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
        test_matrix: ComplianceMatrix,
    ):
        """Only unaddressed requirements are returned as gaps."""
        resp = await client.get(f"/api/v1/analyze/{test_rfp.id}/gaps", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        # REQ-001 is unaddressed, REQ-002 is addressed
        assert data["total_open"] == 1
        assert data["mandatory_open"] == 1
        assert len(data["gaps"]) == 1
        assert data["gaps"][0]["id"] == "REQ-001"

    @pytest.mark.asyncio
    async def test_gaps_all_addressed_returns_zero(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
        db_session: AsyncSession,
    ):
        """When all requirements are addressed, gaps list is empty."""
        matrix = ComplianceMatrix(
            rfp_id=test_rfp.id,
            requirements=[
                {
                    "id": "REQ-001",
                    "section": "L.1",
                    "requirement_text": "Technical approach",
                    "importance": "mandatory",
                    "is_addressed": True,
                    "status": "addressed",
                    "category": None,
                    "page_reference": None,
                    "keywords": [],
                    "notes": None,
                },
            ],
            total_requirements=1,
            mandatory_count=1,
            addressed_count=1,
        )
        db_session.add(matrix)
        await db_session.commit()

        resp = await client.get(f"/api/v1/analyze/{test_rfp.id}/gaps", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_open"] == 0
        assert data["mandatory_open"] == 0
        assert data["gaps"] == []


# ---------------------------------------------------------------------------
# POST /api/v1/analyze/{rfp_id}/matrix — Add requirement
# ---------------------------------------------------------------------------


class TestAddComplianceRequirement:
    """Tests for POST /api/v1/analyze/{rfp_id}/matrix."""

    @pytest.mark.asyncio
    async def test_add_requires_auth(self, client: AsyncClient, test_rfp: RFP):
        """Returns 401 without auth token."""
        resp = await client.post(
            f"/api/v1/analyze/{test_rfp.id}/matrix",
            json={
                "section": "M.1",
                "requirement_text": "New req",
                "importance": "mandatory",
            },
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_add_idor(self, client: AsyncClient, other_user_headers: dict, test_rfp: RFP):
        """Another user cannot add requirements to first user's RFP."""
        resp = await client.post(
            f"/api/v1/analyze/{test_rfp.id}/matrix",
            headers=other_user_headers,
            json={
                "section": "M.1",
                "requirement_text": "New req",
                "importance": "mandatory",
            },
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_add_creates_matrix_if_missing(
        self, client: AsyncClient, auth_headers: dict, test_rfp: RFP
    ):
        """Adding to an RFP with no matrix creates a new one."""
        resp = await client.post(
            f"/api/v1/analyze/{test_rfp.id}/matrix",
            headers=auth_headers,
            json={
                "section": "M.1",
                "requirement_text": "New req",
                "importance": "mandatory",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_requirements"] == 1
        assert data["mandatory_count"] == 1
        assert len(data["requirements"]) == 1
        # Auto-generated ID
        assert data["requirements"][0]["id"].startswith("REQ-")

    @pytest.mark.asyncio
    async def test_add_appends_to_existing_matrix(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
        test_matrix: ComplianceMatrix,
    ):
        """Adding a requirement appends to existing matrix."""
        resp = await client.post(
            f"/api/v1/analyze/{test_rfp.id}/matrix",
            headers=auth_headers,
            json={
                "section": "M.3",
                "requirement_text": "Management approach",
                "importance": "evaluated",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_requirements"] == 3
        assert len(data["requirements"]) == 3

    @pytest.mark.asyncio
    async def test_add_duplicate_id_returns_409(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
        test_matrix: ComplianceMatrix,
    ):
        """Adding a requirement with an existing ID returns 409."""
        resp = await client.post(
            f"/api/v1/analyze/{test_rfp.id}/matrix",
            headers=auth_headers,
            json={
                "id": "REQ-001",
                "section": "M.1",
                "requirement_text": "Duplicate",
                "importance": "mandatory",
            },
        )
        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_add_with_explicit_id(
        self, client: AsyncClient, auth_headers: dict, test_rfp: RFP
    ):
        """Adding a requirement with an explicit ID uses that ID."""
        resp = await client.post(
            f"/api/v1/analyze/{test_rfp.id}/matrix",
            headers=auth_headers,
            json={
                "id": "CUSTOM-001",
                "section": "L.5",
                "requirement_text": "Custom req",
                "importance": "optional",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["requirements"][0]["id"] == "CUSTOM-001"


# ---------------------------------------------------------------------------
# PATCH /api/v1/analyze/{rfp_id}/matrix/{requirement_id} — Update requirement
# ---------------------------------------------------------------------------


class TestUpdateComplianceRequirement:
    """Tests for PATCH /api/v1/analyze/{rfp_id}/matrix/{requirement_id}."""

    @pytest.mark.asyncio
    async def test_update_requires_auth(self, client: AsyncClient, test_rfp: RFP):
        """Returns 401 without auth token."""
        resp = await client.patch(
            f"/api/v1/analyze/{test_rfp.id}/matrix/REQ-001",
            json={"is_addressed": True},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_update_idor(self, client: AsyncClient, other_user_headers: dict, test_rfp: RFP):
        """Another user cannot update requirements on first user's RFP."""
        resp = await client.patch(
            f"/api/v1/analyze/{test_rfp.id}/matrix/REQ-001",
            headers=other_user_headers,
            json={"is_addressed": True},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_no_matrix_returns_404(
        self, client: AsyncClient, auth_headers: dict, test_rfp: RFP
    ):
        """Updating when no matrix exists returns 404."""
        resp = await client.patch(
            f"/api/v1/analyze/{test_rfp.id}/matrix/REQ-001",
            headers=auth_headers,
            json={"is_addressed": True},
        )
        assert resp.status_code == 404
        assert "Run analysis first" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_requirement_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
        test_matrix: ComplianceMatrix,
    ):
        """Updating a non-existent requirement returns 404."""
        resp = await client.patch(
            f"/api/v1/analyze/{test_rfp.id}/matrix/NONEXIST-999",
            headers=auth_headers,
            json={"is_addressed": True},
        )
        assert resp.status_code == 404
        assert "Requirement not found" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_marks_addressed(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
        test_matrix: ComplianceMatrix,
    ):
        """Marking a requirement as addressed updates counts."""
        resp = await client.patch(
            f"/api/v1/analyze/{test_rfp.id}/matrix/REQ-001",
            headers=auth_headers,
            json={"is_addressed": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["addressed_count"] == 2
        # Find the updated requirement
        req = next(r for r in data["requirements"] if r["id"] == "REQ-001")
        assert req["is_addressed"] is True

    @pytest.mark.asyncio
    async def test_update_changes_text(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
        test_matrix: ComplianceMatrix,
    ):
        """Updating requirement_text persists the change."""
        resp = await client.patch(
            f"/api/v1/analyze/{test_rfp.id}/matrix/REQ-001",
            headers=auth_headers,
            json={"requirement_text": "Updated technical approach description"},
        )
        assert resp.status_code == 200
        req = next(r for r in resp.json()["requirements"] if r["id"] == "REQ-001")
        assert req["requirement_text"] == "Updated technical approach description"


# ---------------------------------------------------------------------------
# DELETE /api/v1/analyze/{rfp_id}/matrix/{requirement_id} — Delete requirement
# ---------------------------------------------------------------------------


class TestDeleteComplianceRequirement:
    """Tests for DELETE /api/v1/analyze/{rfp_id}/matrix/{requirement_id}."""

    @pytest.mark.asyncio
    async def test_delete_requires_auth(self, client: AsyncClient, test_rfp: RFP):
        """Returns 401 without auth token."""
        resp = await client.delete(f"/api/v1/analyze/{test_rfp.id}/matrix/REQ-001")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_idor(self, client: AsyncClient, other_user_headers: dict, test_rfp: RFP):
        """Another user cannot delete requirements on first user's RFP."""
        resp = await client.delete(
            f"/api/v1/analyze/{test_rfp.id}/matrix/REQ-001",
            headers=other_user_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_no_matrix_returns_404(
        self, client: AsyncClient, auth_headers: dict, test_rfp: RFP
    ):
        """Deleting when no matrix exists returns 404."""
        resp = await client.delete(
            f"/api/v1/analyze/{test_rfp.id}/matrix/REQ-001",
            headers=auth_headers,
        )
        assert resp.status_code == 404
        assert "Run analysis first" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_requirement_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
        test_matrix: ComplianceMatrix,
    ):
        """Deleting a non-existent requirement returns 404."""
        resp = await client.delete(
            f"/api/v1/analyze/{test_rfp.id}/matrix/NONEXIST-999",
            headers=auth_headers,
        )
        assert resp.status_code == 404
        assert "Requirement not found" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_removes_requirement(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
        test_matrix: ComplianceMatrix,
    ):
        """Deleting a requirement removes it and recalculates counts."""
        resp = await client.delete(
            f"/api/v1/analyze/{test_rfp.id}/matrix/REQ-001",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["requirement_id"] == "REQ-001"
        assert data["message"] == "Requirement deleted"

        # Verify the matrix has one fewer requirement
        matrix_resp = await client.get(
            f"/api/v1/analyze/{test_rfp.id}/matrix", headers=auth_headers
        )
        matrix_data = matrix_resp.json()
        assert matrix_data["total_requirements"] == 1
        assert len(matrix_data["requirements"]) == 1
        assert matrix_data["requirements"][0]["id"] == "REQ-002"


# ---------------------------------------------------------------------------
# POST /api/v1/analyze/{rfp_id}/filter — Trigger killer filter
# ---------------------------------------------------------------------------


class TestTriggerKillerFilter:
    """Tests for POST /api/v1/analyze/{rfp_id}/filter."""

    @pytest.mark.asyncio
    async def test_filter_requires_auth(self, client: AsyncClient, test_rfp: RFP):
        """Returns 401 without auth token or user_id."""
        resp = await client.post(f"/api/v1/analyze/{test_rfp.id}/filter")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_filter_rfp_not_found(self, client: AsyncClient, auth_headers: dict):
        """Non-existent RFP returns 404."""
        resp = await client.post("/api/v1/analyze/999999/filter", headers=auth_headers)
        assert resp.status_code == 404
