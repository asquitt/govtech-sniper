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
            "canada_buyandsell",
            "canada_provincial",
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
        monkeypatch,
    ):
        sled_provider = get_provider("sled_bidnet")
        assert sled_provider is not None

        async def fake_sled_search(_params):
            return [
                RawOpportunity(
                    external_id="SLED-TEST-001",
                    title="State Cybersecurity Modernization",
                    agency="State of Virginia",
                    description="SLED cybersecurity services.",
                    posted_date="2026-02-01",
                    response_deadline=None,
                    estimated_value=500000,
                    naics_code="541512",
                    source_url="https://www.bidnetdirect.com/fake",
                    source_type="sled",
                    raw_data={"test": True},
                )
            ]

        monkeypatch.setattr(sled_provider, "search", fake_sled_search)

        sled_response = await client.post(
            "/api/v1/data-sources/sled_bidnet/search",
            headers=auth_headers,
            json={"keywords": "cybersecurity", "limit": 10},
        )
        assert sled_response.status_code == 200
        sled_payload = sled_response.json()
        assert sled_payload["count"] >= 1
        assert sled_payload["results"][0]["source_type"] == "sled"

        dibbs_provider = get_provider("dibbs")
        assert dibbs_provider is not None

        async def fake_dibbs_search(_params):
            return [
                RawOpportunity(
                    external_id="DIBBS-TEST-001",
                    title="Network Router Procurement",
                    agency="DLA",
                    description="DIBBS router procurement.",
                    posted_date="2026-02-01",
                    response_deadline=None,
                    estimated_value=75000,
                    naics_code="334210",
                    source_url="https://www.dibbs.bsm.dla.mil/fake",
                    source_type="dibbs",
                    raw_data={"test": True},
                )
            ]

        monkeypatch.setattr(dibbs_provider, "search", fake_dibbs_search)

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
    async def test_provider_list_includes_maturity(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        response = await client.get("/api/v1/data-sources", headers=auth_headers)
        assert response.status_code == 200
        providers = response.json()
        for provider in providers:
            assert "maturity" in provider, f"Missing maturity on {provider['provider_name']}"
            assert provider["maturity"] in ("LIVE", "HYBRID", "SAMPLE")
            assert "last_live_sync" in provider
            assert "record_count_estimate" in provider

    @pytest.mark.asyncio
    async def test_contract_vehicle_feed_ingest(
        self,
        client: AsyncClient,
        auth_headers: dict,
        monkeypatch,
    ):
        oasis_provider = get_provider("oasis")
        assert oasis_provider is not None

        async def fake_oasis_search(_params):
            return [
                RawOpportunity(
                    external_id="OASIS-TEST-001",
                    title="OASIS Mission Support Services",
                    agency="GSA",
                    description="OASIS contract vehicle task order.",
                    posted_date="2026-02-01",
                    response_deadline=None,
                    estimated_value=2000000,
                    naics_code="541611",
                    source_url="https://sam.gov/opp/fake",
                    source_type="oasis",
                    raw_data={"test": True},
                )
            ]

        monkeypatch.setattr(oasis_provider, "search", fake_oasis_search)

        response = await client.post(
            "/api/v1/data-sources/oasis/ingest",
            headers=auth_headers,
            json={"keywords": "mission", "limit": 5},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["searched"] >= 1
        assert payload["created"] >= 1

    @pytest.mark.asyncio
    async def test_canadian_provincial_ingest_sets_currency_and_jurisdiction(
        self,
        client: AsyncClient,
        auth_headers: dict,
        monkeypatch,
    ):
        provider = get_provider("canada_provincial")
        assert provider is not None

        async def fake_search(_params):
            return [
                RawOpportunity(
                    external_id="CA-ON-TEST-001",
                    title="Ontario Cybersecurity Services",
                    agency="Ontario Shared Services",
                    description="Provincial managed security services RFP.",
                    posted_date="2026-02-12",
                    response_deadline="2026-03-15T17:00:00",
                    estimated_value=800000,
                    naics_code="541512",
                    source_url="https://ontariotenders.bravosolution.com/",
                    source_type="canada_provincial",
                    jurisdiction="CA-ON",
                    currency="CAD",
                    raw_data={"provincial_portal_url": "https://ontariotenders.bravosolution.com/"},
                )
            ]

        monkeypatch.setattr(provider, "search", fake_search)

        ingest_response = await client.post(
            "/api/v1/data-sources/canada_provincial/ingest",
            headers=auth_headers,
            json={"keywords": "cybersecurity", "limit": 5},
        )
        assert ingest_response.status_code == 200
        assert ingest_response.json()["created"] == 1

        list_response = await client.get(
            "/api/v1/rfps",
            headers=auth_headers,
            params={"jurisdiction": "CA-ON", "currency": "CAD"},
        )
        assert list_response.status_code == 200
        records = list_response.json()
        assert len(records) == 1
        assert records[0]["source_type"] == "canada_provincial"
        assert records[0]["jurisdiction"] == "CA-ON"
        assert records[0]["currency"] == "CAD"
