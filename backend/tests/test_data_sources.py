"""
RFP Sniper - Data Source Integration Tests
==========================================
Tests for provider listing, search, ingest idempotency, and health endpoints.
"""

import pytest
from httpx import AsyncClient

from app.services.data_providers import RawOpportunity, get_provider


class TestDataSources:
    @pytest.mark.asyncio
    async def test_list_providers(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/data-sources", headers=auth_headers)
        assert response.status_code == 200
        providers = response.json()
        provider_names = {provider["provider_name"] for provider in providers}
        assert {
            "gsa_ebuy",
            "fpds",
            "usaspending",
            "sewp",
            "gsa_mas",
            "cio_sp3",
            "ites",
            "oasis",
            "sled_bidnet",
            "dibbs",
        }.issubset(provider_names)

    @pytest.mark.asyncio
    async def test_search_ingest_and_deduplicate(
        self,
        client: AsyncClient,
        auth_headers: dict,
        monkeypatch,
    ):
        provider = get_provider("fpds")
        assert provider is not None

        async def fake_search(_params):
            return [
                RawOpportunity(
                    external_id="FPDS-TEST-001",
                    title="Cybersecurity Support Services",
                    agency="Department of Defense",
                    description="Award data for cybersecurity support services.",
                    posted_date="2026-02-01",
                    response_deadline=None,
                    estimated_value=1250000,
                    naics_code="541512",
                    source_url="https://www.fpds.gov/ezsearch/fake",
                    source_type="fpds",
                    raw_data={"test": True},
                )
            ]

        monkeypatch.setattr(provider, "search", fake_search)

        search_response = await client.post(
            "/api/v1/data-sources/fpds/search",
            headers=auth_headers,
            json={"keywords": "cybersecurity", "limit": 10},
        )
        assert search_response.status_code == 200
        assert search_response.json()["count"] == 1
        assert search_response.json()["results"][0]["external_id"] == "FPDS-TEST-001"

        first_ingest = await client.post(
            "/api/v1/data-sources/fpds/ingest",
            headers=auth_headers,
            json={"keywords": "cybersecurity", "limit": 10},
        )
        assert first_ingest.status_code == 200
        assert first_ingest.json()["created"] == 1
        assert first_ingest.json()["skipped"] == 0

        second_ingest = await client.post(
            "/api/v1/data-sources/fpds/ingest",
            headers=auth_headers,
            json={"keywords": "cybersecurity", "limit": 10},
        )
        assert second_ingest.status_code == 200
        assert second_ingest.json()["created"] == 0
        assert second_ingest.json()["skipped"] == 1

    @pytest.mark.asyncio
    async def test_provider_health_endpoint(
        self,
        client: AsyncClient,
        auth_headers: dict,
        monkeypatch,
    ):
        provider = get_provider("usaspending")
        assert provider is not None

        async def fake_health():
            return True

        monkeypatch.setattr(provider, "health_check", fake_health)

        response = await client.get(
            "/api/v1/data-sources/usaspending/health",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["healthy"] is True

    @pytest.mark.asyncio
    async def test_sled_and_dibbs_provider_search(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        sled_response = await client.post(
            "/api/v1/data-sources/sled_bidnet/search",
            headers=auth_headers,
            json={"keywords": "cybersecurity", "limit": 10},
        )
        assert sled_response.status_code == 200
        sled_payload = sled_response.json()
        assert sled_payload["count"] >= 1
        assert sled_payload["results"][0]["source_type"] == "sled"

        dibbs_response = await client.post(
            "/api/v1/data-sources/dibbs/search",
            headers=auth_headers,
            json={"keywords": "router", "limit": 10},
        )
        assert dibbs_response.status_code == 200
        dibbs_payload = dibbs_response.json()
        assert dibbs_payload["count"] >= 1
        assert dibbs_payload["results"][0]["source_type"] == "dibbs"

    @pytest.mark.asyncio
    async def test_contract_vehicle_feed_ingest(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        response = await client.post(
            "/api/v1/data-sources/oasis/ingest",
            headers=auth_headers,
            json={"keywords": "mission", "limit": 5},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["searched"] >= 1
        assert payload["created"] >= 1
