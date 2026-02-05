"""
RFP Sniper - Contact Tests
==========================
Tests for opportunity contact endpoints.
"""

import pytest
from httpx import AsyncClient


class TestContacts:
    @pytest.mark.asyncio
    async def test_contact_crud(self, client: AsyncClient, auth_headers: dict):
        # Create RFP
        response = await client.post(
            "/api/v1/rfps",
            headers=auth_headers,
            json={
                "title": "Contact RFP",
                "solicitation_number": "CNT-001",
                "agency": "Test Agency",
            },
        )
        assert response.status_code == 200
        rfp_id = response.json()["id"]

        # Create contact
        response = await client.post(
            "/api/v1/contacts",
            headers=auth_headers,
            json={
                "rfp_id": rfp_id,
                "name": "Jane Doe",
                "role": "Contracting Officer",
                "email": "jane@example.com",
            },
        )
        assert response.status_code == 200
        contact_id = response.json()["id"]

        # List
        response = await client.get(
            "/api/v1/contacts",
            headers=auth_headers,
            params={"rfp_id": rfp_id},
        )
        assert response.status_code == 200
        contacts = response.json()
        assert len(contacts) == 1
        assert contacts[0]["id"] == contact_id

        # Update
        response = await client.patch(
            f"/api/v1/contacts/{contact_id}",
            headers=auth_headers,
            json={"phone": "555-0100"},
        )
        assert response.status_code == 200
        assert response.json()["phone"] == "555-0100"

        # Delete
        response = await client.delete(
            f"/api/v1/contacts/{contact_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
