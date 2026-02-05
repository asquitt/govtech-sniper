"""
RFP Sniper - Award Tests
========================
Tests for award intelligence endpoints.
"""

import pytest
from httpx import AsyncClient


class TestAwards:
    @pytest.mark.asyncio
    async def test_award_crud(self, client: AsyncClient, auth_headers: dict):
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
