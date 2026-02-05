"""
RFP Sniper - Saved Searches Tests
=================================
Tests for saved search endpoints.
"""

import pytest
from httpx import AsyncClient


class TestSavedSearches:
    @pytest.mark.asyncio
    async def test_saved_search_crud_and_run(self, client: AsyncClient, auth_headers: dict):
        # Seed RFPs
        response = await client.post(
            "/api/v1/rfps",
            headers=auth_headers,
            json={
                "title": "Cybersecurity Support Services",
                "solicitation_number": "W912-TEST-001",
                "agency": "Department of Defense",
                "naics_code": "541512",
                "set_aside": "Small Business",
                "estimated_value": 1000000,
                "source_type": "federal",
                "contract_vehicle": "SEWP",
            },
        )
        assert response.status_code == 200

        response = await client.post(
            "/api/v1/rfps",
            headers=auth_headers,
            json={
                "title": "Statewide Network Upgrade",
                "solicitation_number": "SLED-TEST-002",
                "agency": "State of Virginia",
                "naics_code": "541513",
                "set_aside": "None",
                "estimated_value": 2500000,
                "source_type": "sled",
                "jurisdiction": "VA",
            },
        )
        assert response.status_code == 200

        # Create saved search
        response = await client.post(
            "/api/v1/saved-searches",
            headers=auth_headers,
            json={
                "name": "Cyber Federal",
                "filters": {
                    "keywords": ["Cybersecurity"],
                    "agencies": ["Department of Defense"],
                    "min_value": 500000,
                    "source_types": ["federal"],
                },
            },
        )
        assert response.status_code == 200
        search_id = response.json()["id"]

        # List
        response = await client.get("/api/v1/saved-searches", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 1

        # Run
        response = await client.post(
            f"/api/v1/saved-searches/{search_id}/run",
            headers=auth_headers,
            json={},
        )
        assert response.status_code == 200
        run_result = response.json()
        assert run_result["match_count"] == 1
        assert run_result["matches"][0]["title"] == "Cybersecurity Support Services"

        # Update
        response = await client.patch(
            f"/api/v1/saved-searches/{search_id}",
            headers=auth_headers,
            json={"name": "Cyber Federal Updated", "is_active": False},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Cyber Federal Updated"

        # Delete
        response = await client.delete(
            f"/api/v1/saved-searches/{search_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
