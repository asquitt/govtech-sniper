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

    @pytest.mark.asyncio
    async def test_extract_search_and_agency_directory(
        self, client: AsyncClient, auth_headers: dict
    ):
        # Create RFP with deterministic contact-extractor trigger phrase.
        create_rfp = await client.post(
            "/api/v1/rfps",
            headers=auth_headers,
            json={
                "title": "Extraction RFP",
                "solicitation_number": "CNT-EXTRACT-001",
                "agency": "Department of Energy",
                "description": "Please direct questions to the Contracting Officer.",
            },
        )
        assert create_rfp.status_code == 200
        rfp_id = create_rfp.json()["id"]

        extract = await client.post(
            f"/api/v1/contacts/extract/{rfp_id}",
            headers=auth_headers,
        )
        assert extract.status_code == 200
        extracted_contacts = extract.json()
        assert len(extracted_contacts) >= 1
        assert extracted_contacts[0]["role"] == "Contracting Officer"
        extracted_name = extracted_contacts[0]["name"]

        # Extract now auto-links contacts to the source opportunity.
        list_contacts = await client.get(
            "/api/v1/contacts",
            headers=auth_headers,
            params={"rfp_id": rfp_id},
        )
        assert list_contacts.status_code == 200
        linked_contacts = list_contacts.json()
        assert len(linked_contacts) >= 1
        assert linked_contacts[0]["name"] == extracted_name
        assert linked_contacts[0]["source"] == "ai_extracted"
        assert rfp_id in (linked_contacts[0]["linked_rfp_ids"] or [])

        # Creating same contact again should link/dedupe instead of duplicating.
        create_contact = await client.post(
            "/api/v1/contacts",
            headers=auth_headers,
            json={
                "rfp_id": rfp_id,
                "name": extracted_name,
                "role": extracted_contacts[0]["role"],
                "agency": "Department of Energy",
                "source": "ai_extracted",
            },
        )
        assert create_contact.status_code == 200
        assert create_contact.json()["id"] == linked_contacts[0]["id"]

        search = await client.get(
            "/api/v1/contacts/search",
            headers=auth_headers,
            params={"agency": "Energy"},
        )
        assert search.status_code == 200
        assert len(search.json()) >= 1

        # Extract from a second opportunity and verify multi-opportunity linking.
        create_rfp_2 = await client.post(
            "/api/v1/rfps",
            headers=auth_headers,
            json={
                "title": "Extraction RFP 2",
                "solicitation_number": "CNT-EXTRACT-002",
                "agency": "Department of Energy",
                "description": "Questions should go to the Contracting Officer.",
            },
        )
        assert create_rfp_2.status_code == 200
        rfp_id_2 = create_rfp_2.json()["id"]

        extract_2 = await client.post(
            f"/api/v1/contacts/extract/{rfp_id_2}",
            headers=auth_headers,
        )
        assert extract_2.status_code == 200

        search_after_second_extract = await client.get(
            "/api/v1/contacts/search",
            headers=auth_headers,
            params={"name": extracted_name},
        )
        assert search_after_second_extract.status_code == 200
        assert len(search_after_second_extract.json()) == 1
        linked = search_after_second_extract.json()[0]["linked_rfp_ids"] or []
        assert rfp_id in linked
        assert rfp_id_2 in linked

        upsert_agency = await client.post(
            "/api/v1/contacts/agencies",
            headers=auth_headers,
            json={
                "agency_name": "Department of Energy",
                "office": "Office of Procurement",
                "website": "energy.gov",
            },
        )
        assert upsert_agency.status_code == 200

        list_agencies = await client.get(
            "/api/v1/contacts/agencies",
            headers=auth_headers,
        )
        assert list_agencies.status_code == 200
        doe_agency = next(
            (
                item
                for item in list_agencies.json()
                if item["agency_name"] == "Department of Energy"
            ),
            None,
        )
        assert doe_agency is not None
        assert doe_agency["primary_contact_id"] is not None
