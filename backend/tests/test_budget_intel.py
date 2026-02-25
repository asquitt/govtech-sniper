"""
RFP Sniper - Budget Intelligence Tests
======================================
Integration tests for budget intelligence CRUD endpoints.
"""

import pytest
from httpx import AsyncClient

from app.models.rfp import RFP

# ---- Auth guards ----


class TestBudgetIntelAuth:
    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/budget-intel")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_create_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/budget-intel", json={"title": "NoAuth Budget"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_update_requires_auth(self, client: AsyncClient):
        resp = await client.patch("/api/v1/budget-intel/1", json={"title": "X"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_requires_auth(self, client: AsyncClient):
        resp = await client.delete("/api/v1/budget-intel/1")
        assert resp.status_code == 401


# ---- CRUD happy path ----


class TestBudgetIntelCRUD:
    @pytest.mark.asyncio
    async def test_full_crud_cycle(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
    ):
        response = await client.post(
            "/api/v1/budget-intel",
            headers=auth_headers,
            json={
                "rfp_id": test_rfp.id,
                "title": "FY26 Budget",
                "fiscal_year": 2026,
                "amount": 1200000,
                "source_url": "https://example.com/budget",
            },
        )
        assert response.status_code == 200
        record_id = response.json()["id"]

        response = await client.get(
            "/api/v1/budget-intel",
            headers=auth_headers,
            params={"rfp_id": test_rfp.id},
        )
        assert response.status_code == 200
        assert len(response.json()) == 1

        response = await client.patch(
            f"/api/v1/budget-intel/{record_id}",
            headers=auth_headers,
            json={"notes": "Updated notes"},
        )
        assert response.status_code == 200
        assert response.json()["notes"] == "Updated notes"

        response = await client.delete(
            f"/api/v1/budget-intel/{record_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200


# ---- Create edge cases ----


class TestBudgetIntelCreate:
    @pytest.mark.asyncio
    async def test_create_without_rfp(self, client: AsyncClient, auth_headers: dict):
        """Budget intel can be standalone (no rfp_id)."""
        resp = await client.post(
            "/api/v1/budget-intel",
            headers=auth_headers,
            json={
                "title": "Standalone Budget Entry",
                "fiscal_year": 2025,
                "amount": 500000,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Standalone Budget Entry"
        assert data["rfp_id"] is None

    @pytest.mark.asyncio
    async def test_create_with_invalid_rfp_returns_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.post(
            "/api/v1/budget-intel",
            headers=auth_headers,
            json={"rfp_id": 99999, "title": "Bad RFP Budget"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create_with_all_fields(
        self, client: AsyncClient, auth_headers: dict, test_rfp: RFP
    ):
        resp = await client.post(
            "/api/v1/budget-intel",
            headers=auth_headers,
            json={
                "rfp_id": test_rfp.id,
                "title": "Complete Budget Record",
                "fiscal_year": 2027,
                "amount": 3500000.50,
                "source_url": "https://usaspending.gov/budget/xyz",
                "notes": "Critical appropriation for IT modernization.",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["fiscal_year"] == 2027
        assert data["amount"] == 3500000.50
        assert data["source_url"] == "https://usaspending.gov/budget/xyz"
        assert data["notes"] == "Critical appropriation for IT modernization."


# ---- List edge cases ----


class TestBudgetIntelList:
    @pytest.mark.asyncio
    async def test_list_empty(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/budget-intel", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_all_no_filter(self, client: AsyncClient, auth_headers: dict):
        """Create two records, list without filter returns both."""
        await client.post(
            "/api/v1/budget-intel",
            headers=auth_headers,
            json={"title": "Budget A", "fiscal_year": 2025},
        )
        await client.post(
            "/api/v1/budget-intel",
            headers=auth_headers,
            json={"title": "Budget B", "fiscal_year": 2026},
        )
        resp = await client.get("/api/v1/budget-intel", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    @pytest.mark.asyncio
    async def test_list_filter_by_rfp(self, client: AsyncClient, auth_headers: dict, test_rfp: RFP):
        """Only records linked to the specified rfp_id are returned."""
        await client.post(
            "/api/v1/budget-intel",
            headers=auth_headers,
            json={"rfp_id": test_rfp.id, "title": "Linked Budget"},
        )
        await client.post(
            "/api/v1/budget-intel",
            headers=auth_headers,
            json={"title": "Unlinked Budget"},
        )
        resp = await client.get(
            "/api/v1/budget-intel",
            headers=auth_headers,
            params={"rfp_id": test_rfp.id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["title"] == "Linked Budget"


# ---- Update/Delete edge cases ----


class TestBudgetIntelUpdateDelete:
    @pytest.mark.asyncio
    async def test_update_not_found(self, client: AsyncClient, auth_headers: dict):
        resp = await client.patch(
            "/api/v1/budget-intel/99999",
            headers=auth_headers,
            json={"title": "Ghost"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_not_found(self, client: AsyncClient, auth_headers: dict):
        resp = await client.delete("/api/v1/budget-intel/99999", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_multiple_fields(self, client: AsyncClient, auth_headers: dict):
        create = await client.post(
            "/api/v1/budget-intel",
            headers=auth_headers,
            json={"title": "Original", "fiscal_year": 2025, "amount": 100},
        )
        record_id = create.json()["id"]

        resp = await client.patch(
            f"/api/v1/budget-intel/{record_id}",
            headers=auth_headers,
            json={
                "title": "Updated Title",
                "fiscal_year": 2027,
                "amount": 9999,
                "notes": "New notes",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Updated Title"
        assert data["fiscal_year"] == 2027
        assert data["amount"] == 9999
        assert data["notes"] == "New notes"

    @pytest.mark.asyncio
    async def test_delete_then_list_empty(self, client: AsyncClient, auth_headers: dict):
        create = await client.post(
            "/api/v1/budget-intel",
            headers=auth_headers,
            json={"title": "Temp Budget"},
        )
        record_id = create.json()["id"]

        await client.delete(f"/api/v1/budget-intel/{record_id}", headers=auth_headers)

        resp = await client.get("/api/v1/budget-intel", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 0
