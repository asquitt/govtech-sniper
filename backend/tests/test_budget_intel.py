"""
RFP Sniper - Budget Intelligence Tests
======================================
Tests for budget intelligence CRUD.
"""

import pytest
from httpx import AsyncClient

from app.models.rfp import RFP


class TestBudgetIntel:
    @pytest.mark.asyncio
    async def test_budget_intel_crud(
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
