"""
RFP Sniper - Award Tests
========================
Integration tests for award intelligence endpoints.
"""

import pytest
from httpx import AsyncClient

from app.models.rfp import RFP

# ---- Auth guards ----


class TestAwardAuth:
    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/awards")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_create_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/awards", json={"awardee_name": "NoAuth Corp"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_update_requires_auth(self, client: AsyncClient):
        resp = await client.patch("/api/v1/awards/1", json={"awardee_name": "X"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_requires_auth(self, client: AsyncClient):
        resp = await client.delete("/api/v1/awards/1")
        assert resp.status_code == 401


# ---- CRUD happy path ----


class TestAwardCRUD:
    @pytest.mark.asyncio
    async def test_full_crud_cycle(self, client: AsyncClient, auth_headers: dict):
        # Create RFP
        response = await client.post(
            "/api/v1/rfps",
            headers=auth_headers,
            json={
                "title": "Awarded RFP",
                "solicitation_number": "AWD-001",
                "agency": "Test Agency",
            },
        )
        assert response.status_code == 200
        rfp_id = response.json()["id"]

        # Create award
        response = await client.post(
            "/api/v1/awards",
            headers=auth_headers,
            json={
                "rfp_id": rfp_id,
                "awardee_name": "Acme Corp",
                "award_amount": 500000,
                "contract_vehicle": "GSA Schedule",
            },
        )
        assert response.status_code == 200
        award_id = response.json()["id"]

        # List awards
        response = await client.get(
            "/api/v1/awards",
            headers=auth_headers,
            params={"rfp_id": rfp_id},
        )
        assert response.status_code == 200
        awards = response.json()
        assert len(awards) == 1
        assert awards[0]["id"] == award_id

        # Update
        response = await client.patch(
            f"/api/v1/awards/{award_id}",
            headers=auth_headers,
            json={"awardee_name": "Updated Corp"},
        )
        assert response.status_code == 200
        assert response.json()["awardee_name"] == "Updated Corp"

        # Delete
        response = await client.delete(
            f"/api/v1/awards/{award_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200


# ---- Create edge cases ----


class TestAwardCreate:
    @pytest.mark.asyncio
    async def test_create_without_rfp(self, client: AsyncClient, auth_headers: dict):
        """Awards can be standalone (no rfp_id)."""
        resp = await client.post(
            "/api/v1/awards",
            headers=auth_headers,
            json={
                "awardee_name": "Standalone Corp",
                "award_amount": 250000,
                "agency": "DoD",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["awardee_name"] == "Standalone Corp"
        assert data["rfp_id"] is None

    @pytest.mark.asyncio
    async def test_create_with_invalid_rfp_returns_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.post(
            "/api/v1/awards",
            headers=auth_headers,
            json={"rfp_id": 99999, "awardee_name": "Bad RFP Corp"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create_with_all_fields(
        self, client: AsyncClient, auth_headers: dict, test_rfp: RFP
    ):
        resp = await client.post(
            "/api/v1/awards",
            headers=auth_headers,
            json={
                "rfp_id": test_rfp.id,
                "awardee_name": "Full Record Inc",
                "award_amount": 9999999,
                "notice_id": "N-123",
                "solicitation_number": "SOL-456",
                "contract_number": "GS-35F-0001",
                "agency": "GSA",
                "contract_vehicle": "MAS",
                "naics_code": "541512",
                "set_aside": "8(a)",
                "place_of_performance": "Washington, DC",
                "description": "Full services contract.",
                "source_url": "https://sam.gov/award/123",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["naics_code"] == "541512"
        assert data["set_aside"] == "8(a)"
        assert data["description"] == "Full services contract."


# ---- List edge cases ----


class TestAwardList:
    @pytest.mark.asyncio
    async def test_list_empty(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/awards", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_all_no_filter(self, client: AsyncClient, auth_headers: dict):
        """Create two awards for different RFPs, list without filter returns both."""
        await client.post(
            "/api/v1/awards",
            headers=auth_headers,
            json={"awardee_name": "Corp A", "award_amount": 100},
        )
        await client.post(
            "/api/v1/awards",
            headers=auth_headers,
            json={"awardee_name": "Corp B", "award_amount": 200},
        )
        resp = await client.get("/api/v1/awards", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    @pytest.mark.asyncio
    async def test_list_respects_limit(self, client: AsyncClient, auth_headers: dict):
        for i in range(5):
            await client.post(
                "/api/v1/awards",
                headers=auth_headers,
                json={"awardee_name": f"Corp {i}"},
            )
        resp = await client.get("/api/v1/awards", headers=auth_headers, params={"limit": 2})
        assert resp.status_code == 200
        assert len(resp.json()) == 2


# ---- Update/Delete edge cases ----


class TestAwardUpdateDelete:
    @pytest.mark.asyncio
    async def test_update_not_found(self, client: AsyncClient, auth_headers: dict):
        resp = await client.patch(
            "/api/v1/awards/99999",
            headers=auth_headers,
            json={"awardee_name": "Ghost"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_not_found(self, client: AsyncClient, auth_headers: dict):
        resp = await client.delete("/api/v1/awards/99999", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_multiple_fields(self, client: AsyncClient, auth_headers: dict):
        create = await client.post(
            "/api/v1/awards",
            headers=auth_headers,
            json={"awardee_name": "Original", "award_amount": 100},
        )
        award_id = create.json()["id"]

        resp = await client.patch(
            f"/api/v1/awards/{award_id}",
            headers=auth_headers,
            json={
                "awardee_name": "Updated",
                "award_amount": 999,
                "agency": "New Agency",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["awardee_name"] == "Updated"
        assert data["award_amount"] == 999
        assert data["agency"] == "New Agency"

    @pytest.mark.asyncio
    async def test_delete_then_list_empty(self, client: AsyncClient, auth_headers: dict):
        create = await client.post(
            "/api/v1/awards",
            headers=auth_headers,
            json={"awardee_name": "Temp Corp"},
        )
        award_id = create.json()["id"]

        await client.delete(f"/api/v1/awards/{award_id}", headers=auth_headers)

        resp = await client.get("/api/v1/awards", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 0
