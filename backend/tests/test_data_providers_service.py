"""
Unit tests for data_providers package
======================================
Tests base models, search params, and provider implementations
(GrantsGov, FPDS) with mocked HTTP calls.
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.data_providers.base import (
    DataSourceProvider,
    ProviderMaturity,
    RawOpportunity,
    SearchParams,
)
from app.services.data_providers.fpds import (
    FPDSProvider,
    _parse_atom_feed,
)
from app.services.data_providers.grants_gov import (
    GrantsGovProvider,
    _map_grant_to_raw,
)

# =============================================================================
# Base Models
# =============================================================================


class TestProviderMaturity:
    def test_live_value(self):
        assert ProviderMaturity.LIVE == "LIVE"

    def test_hybrid_value(self):
        assert ProviderMaturity.HYBRID == "HYBRID"

    def test_sample_value(self):
        assert ProviderMaturity.SAMPLE == "SAMPLE"


class TestSearchParams:
    def test_defaults(self):
        params = SearchParams()
        assert params.keywords is None
        assert params.naics_codes is None
        assert params.agency is None
        assert params.days_back == 90
        assert params.limit == 25

    def test_custom_values(self):
        params = SearchParams(
            keywords="cybersecurity",
            naics_codes=["541512"],
            agency="DoD",
            days_back=30,
            limit=10,
        )
        assert params.keywords == "cybersecurity"
        assert params.naics_codes == ["541512"]
        assert params.agency == "DoD"
        assert params.days_back == 30
        assert params.limit == 10


class TestRawOpportunity:
    def test_required_fields(self):
        opp = RawOpportunity(
            external_id="OPP-001",
            title="Test Opportunity",
            source_type="sam_gov",
        )
        assert opp.external_id == "OPP-001"
        assert opp.title == "Test Opportunity"
        assert opp.source_type == "sam_gov"
        assert opp.agency is None
        assert opp.estimated_value is None

    def test_all_fields(self):
        opp = RawOpportunity(
            external_id="OPP-002",
            title="Full Opportunity",
            agency="DoD",
            description="A test opportunity",
            posted_date="2024-01-15",
            response_deadline="2024-02-15",
            estimated_value=1_000_000.0,
            currency="USD",
            jurisdiction="US-Federal",
            naics_code="541512",
            source_url="https://example.com/opp",
            source_type="sam_gov",
            raw_data={"key": "value"},
        )
        assert opp.agency == "DoD"
        assert opp.estimated_value == 1_000_000.0
        assert opp.raw_data == {"key": "value"}


# =============================================================================
# Grants.gov Provider
# =============================================================================


class TestGrantsGovProvider:
    def test_provider_metadata(self):
        provider = GrantsGovProvider()
        assert provider.provider_name == "grants_gov"
        assert provider.display_name == "Grants.gov"
        assert provider.is_active is True
        assert provider.maturity == ProviderMaturity.HYBRID

    @pytest.mark.asyncio
    async def test_search_success(self):
        provider = GrantsGovProvider()
        mock_response = httpx.Response(
            200,
            json={
                "oppHits": [
                    {
                        "id": "123",
                        "title": "Cybersecurity Grant",
                        "agency": "DHS",
                        "openDate": "2024-01-01",
                        "closeDate": "2024-03-01",
                        "awardCeiling": "500000",
                    }
                ]
            },
            request=httpx.Request("POST", "https://example.com"),
        )
        with patch("app.services.data_providers.grants_gov.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            params = SearchParams(keywords="cybersecurity", limit=10)
            results = await provider.search(params)

        assert len(results) == 1
        assert results[0].title == "Cybersecurity Grant"
        assert results[0].agency == "DHS"
        assert results[0].estimated_value == 500000.0
        assert results[0].source_type == "grants_gov"

    @pytest.mark.asyncio
    async def test_search_http_error_returns_empty(self):
        provider = GrantsGovProvider()
        with patch("app.services.data_providers.grants_gov.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(side_effect=httpx.HTTPError("timeout"))
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            params = SearchParams(keywords="test")
            results = await provider.search(params)

        assert results == []

    @pytest.mark.asyncio
    async def test_search_with_naics_codes(self):
        provider = GrantsGovProvider()
        mock_response = httpx.Response(
            200,
            json={"oppHits": []},
            request=httpx.Request("POST", "https://example.com"),
        )
        with patch("app.services.data_providers.grants_gov.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            params = SearchParams(keywords="IT", naics_codes=["541512", "541511"])
            results = await provider.search(params)

        assert results == []
        call_args = mock_instance.post.call_args
        payload = call_args[1]["json"] if "json" in call_args[1] else call_args.kwargs["json"]
        assert "541512" in payload["keyword"]

    @pytest.mark.asyncio
    async def test_get_details_success(self):
        provider = GrantsGovProvider()
        mock_response = httpx.Response(
            200,
            json={
                "id": "456",
                "title": "Detail Grant",
                "agency": "NSF",
            },
            request=httpx.Request("GET", "https://example.com"),
        )
        with patch("app.services.data_providers.grants_gov.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            result = await provider.get_details("456")

        assert result is not None
        assert result.external_id == "456"
        assert result.title == "Detail Grant"

    @pytest.mark.asyncio
    async def test_get_details_http_error(self):
        provider = GrantsGovProvider()
        with patch("app.services.data_providers.grants_gov.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(side_effect=httpx.HTTPError("fail"))
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            result = await provider.get_details("999")

        assert result is None

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        provider = GrantsGovProvider()
        mock_response = httpx.Response(
            200,
            json={},
            request=httpx.Request("POST", "https://example.com"),
        )
        with patch("app.services.data_providers.grants_gov.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            result = await provider.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        provider = GrantsGovProvider()
        with patch("app.services.data_providers.grants_gov.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(side_effect=httpx.HTTPError("down"))
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            result = await provider.health_check()

        assert result is False


class TestMapGrantToRaw:
    def test_maps_standard_fields(self):
        item = {
            "id": "100",
            "title": "Grant Title",
            "agency": "DOE",
            "description": "Desc",
            "openDate": "2024-01-01",
            "closeDate": "2024-03-01",
            "awardCeiling": "250000",
            "cfdaNumber": "81.049",
        }
        opp = _map_grant_to_raw(item)
        assert opp.external_id == "100"
        assert opp.title == "Grant Title"
        assert opp.agency == "DOE"
        assert opp.estimated_value == 250000.0
        assert opp.naics_code == "81.049"
        assert opp.source_type == "grants_gov"

    def test_maps_alternate_field_names(self):
        item = {
            "oppId": "200",
            "oppTitle": "Alt Title",
            "agencyName": "NASA",
            "synopsis": "Synopsis text",
        }
        opp = _map_grant_to_raw(item)
        assert opp.external_id == "200"
        assert opp.title == "Alt Title"
        assert opp.agency == "NASA"
        assert opp.description == "Synopsis text"

    def test_handles_missing_award_ceiling(self):
        item = {"id": "300", "title": "No Value"}
        opp = _map_grant_to_raw(item)
        assert opp.estimated_value is None

    def test_source_url_contains_id(self):
        item = {"id": "400", "title": "URL Test"}
        opp = _map_grant_to_raw(item)
        assert "400" in opp.source_url


# =============================================================================
# FPDS Provider
# =============================================================================


SAMPLE_ATOM_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:ns1="https://www.fpds.gov/FPDS">
  <entry>
    <title>Test Contract Award</title>
    <link href="https://fpds.gov/entry/1"/>
    <id>urn:fpds:1</id>
    <content>
      <ns1:award>
        <ns1:awardID>
          <ns1:awardContractID>
            <ns1:PIID>W12345</ns1:PIID>
          </ns1:awardContractID>
        </ns1:awardID>
        <ns1:contractData>
          <ns1:descriptionOfContractRequirement>IT Services</ns1:descriptionOfContractRequirement>
        </ns1:contractData>
        <ns1:competition>
          <ns1:NAICSCode>541512</ns1:NAICSCode>
        </ns1:competition>
        <ns1:dollarValues>
          <ns1:obligatedAmount>500000.00</ns1:obligatedAmount>
        </ns1:dollarValues>
        <ns1:relevantContractDates>
          <ns1:signedDate>2024-01-15</ns1:signedDate>
        </ns1:relevantContractDates>
        <ns1:purchaserInformation>
          <ns1:contractingOfficeAgencyID name="Dept of Defense"/>
        </ns1:purchaserInformation>
      </ns1:award>
    </content>
  </entry>
</feed>"""


class TestFPDSProvider:
    def test_provider_metadata(self):
        provider = FPDSProvider()
        assert provider.provider_name == "fpds"
        assert provider.display_name == "FPDS"
        assert provider.is_active is True
        assert provider.maturity == ProviderMaturity.HYBRID

    @pytest.mark.asyncio
    async def test_search_success(self):
        provider = FPDSProvider()
        mock_response = httpx.Response(
            200,
            text=SAMPLE_ATOM_XML,
            request=httpx.Request("GET", "https://example.com"),
        )
        with patch("app.services.data_providers.fpds.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            params = SearchParams(keywords="IT", limit=10)
            results = await provider.search(params)

        assert len(results) == 1
        assert results[0].external_id == "W12345"
        assert results[0].naics_code == "541512"
        assert results[0].estimated_value == 500000.0
        assert results[0].source_type == "fpds"

    @pytest.mark.asyncio
    async def test_search_http_error(self):
        provider = FPDSProvider()
        with patch("app.services.data_providers.fpds.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(side_effect=httpx.HTTPError("error"))
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            results = await provider.search(SearchParams(keywords="test"))

        assert results == []

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        provider = FPDSProvider()
        mock_response = httpx.Response(
            200,
            text="<feed/>",
            request=httpx.Request("GET", "https://example.com"),
        )
        with patch("app.services.data_providers.fpds.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            result = await provider.health_check()

        assert result is True


class TestParseAtomFeed:
    def test_parse_valid_xml(self):
        results = _parse_atom_feed(SAMPLE_ATOM_XML, limit=10)
        assert len(results) == 1
        assert results[0].external_id == "W12345"
        assert results[0].title == "Test Contract Award"
        assert results[0].agency == "Dept of Defense"
        assert results[0].description == "IT Services"
        assert results[0].estimated_value == 500000.0
        assert results[0].naics_code == "541512"
        assert results[0].posted_date == "2024-01-15"

    def test_parse_invalid_xml(self):
        results = _parse_atom_feed("not valid xml", limit=10)
        assert results == []

    def test_parse_empty_feed(self):
        xml = """<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
        </feed>"""
        results = _parse_atom_feed(xml, limit=10)
        assert results == []

    def test_parse_respects_limit(self):
        # Two entries, limit 1
        xml = """<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom" xmlns:ns1="https://www.fpds.gov/FPDS">
          <entry><title>A</title><id>1</id></entry>
          <entry><title>B</title><id>2</id></entry>
        </feed>"""
        results = _parse_atom_feed(xml, limit=1)
        assert len(results) == 1


# =============================================================================
# Abstract Base Class
# =============================================================================


class TestDataSourceProviderABC:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            DataSourceProvider()
