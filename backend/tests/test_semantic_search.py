"""Integration tests for semantic search indexing + tenant isolation."""

from datetime import datetime

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password


def _build_rfp_payload(suffix: str, *, title: str, agency: str) -> dict:
    return {
        "title": title,
        "solicitation_number": f"SEM-{suffix}",
        "agency": agency,
        "description": f"{title} solicitation details for semantic indexing.",
    }


class TestSemanticSearch:
    async def test_search_is_user_scoped_and_indexes_rfps(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_headers: dict,
    ) -> None:
        first = await client.post(
            "/api/v1/rfps",
            headers=auth_headers,
            json=_build_rfp_payload(
                "A",
                title="Cloud Migration Alpha Program",
                agency="Department of Energy",
            ),
        )
        assert first.status_code == 200
        first_rfp = first.json()

        other_user = User(
            email="search-other@example.com",
            hashed_password=hash_password("TestPassword123!"),
            full_name="Other Search User",
            company_name="Other Co",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(other_user)

        other_tokens = create_token_pair(other_user.id, other_user.email, other_user.tier)
        other_headers = {"Authorization": f"Bearer {other_tokens.access_token}"}

        second = await client.post(
            "/api/v1/rfps",
            headers=other_headers,
            json=_build_rfp_payload(
                "B",
                title="Drone Surveillance Sustainment",
                agency="Department of Defense",
            ),
        )
        assert second.status_code == 200
        second_rfp = second.json()

        leak_probe = await client.post(
            "/api/v1/search",
            headers=auth_headers,
            json={
                "query": "drone surveillance sustainment",
                "entity_types": ["rfp"],
                "limit": 10,
            },
        )
        assert leak_probe.status_code == 200
        leaked_ids = [item["entity_id"] for item in leak_probe.json()["results"]]
        assert second_rfp["id"] not in leaked_ids

        own_probe = await client.post(
            "/api/v1/search",
            headers=auth_headers,
            json={
                "query": "cloud migration alpha",
                "entity_types": ["rfp"],
                "limit": 10,
            },
        )
        assert own_probe.status_code == 200
        own_ids = [item["entity_id"] for item in own_probe.json()["results"]]
        assert first_rfp["id"] in own_ids

    async def test_search_indexes_contacts_and_sections(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ) -> None:
        contact_create = await client.post(
            "/api/v1/contacts",
            headers=auth_headers,
            json={
                "name": "Jane Capture",
                "agency": "NASA",
                "title": "Contracting Officer",
                "notes": "Leads capture and source selection communications.",
            },
        )
        assert contact_create.status_code == 200
        contact = contact_create.json()

        contact_search = await client.post(
            "/api/v1/search",
            headers=auth_headers,
            json={
                "query": "Jane Capture source selection",
                "entity_types": ["contact"],
                "limit": 10,
            },
        )
        assert contact_search.status_code == 200
        contact_results = contact_search.json()["results"]
        assert any(
            item["entity_type"] == "contact" and item["entity_id"] == contact["id"]
            for item in contact_results
        )

        nonce = int(datetime.utcnow().timestamp())
        rfp_resp = await client.post(
            "/api/v1/rfps",
            headers=auth_headers,
            json={
                "title": f"Semantic Proposal Parent {nonce}",
                "solicitation_number": f"SEM-PROP-{nonce}",
                "agency": "GSA",
            },
        )
        assert rfp_resp.status_code == 200
        rfp = rfp_resp.json()

        proposal_resp = await client.post(
            "/api/v1/draft/proposals",
            headers=auth_headers,
            json={
                "rfp_id": rfp["id"],
                "title": f"Semantic Proposal {nonce}",
            },
        )
        assert proposal_resp.status_code == 200
        proposal = proposal_resp.json()

        section_resp = await client.post(
            f"/api/v1/draft/proposals/{proposal['id']}/sections",
            headers=auth_headers,
            json={
                "title": "Technical Volume",
                "section_number": "1.0",
                "requirement_id": f"REQ-{nonce}",
                "requirement_text": "Describe secure cloud delivery controls.",
                "display_order": 1,
            },
        )
        assert section_resp.status_code == 200
        section = section_resp.json()

        section_update = await client.patch(
            f"/api/v1/draft/sections/{section['id']}",
            headers=auth_headers,
            json={
                "final_content": "Zero trust cloud controls with automated continuous compliance evidence.",
            },
        )
        assert section_update.status_code == 200

        section_search = await client.post(
            "/api/v1/search",
            headers=auth_headers,
            json={
                "query": "continuous compliance evidence zero trust cloud",
                "entity_types": ["proposal_section"],
                "limit": 10,
            },
        )
        assert section_search.status_code == 200
        section_results = section_search.json()["results"]
        assert any(
            item["entity_type"] == "proposal_section" and item["entity_id"] == section["id"]
            for item in section_results
        )
