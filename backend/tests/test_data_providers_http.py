"""
Unit tests for data_providers/ HTTP operations — search, get_details, health_check.

Each provider makes HTTP calls with httpx. We mock httpx.AsyncClient to test
mapping logic and error handling without hitting real APIs.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.data_providers.base import RawOpportunity, SearchParams

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_httpx_response(
    status_code: int = 200,
    json_data: dict | list | None = None,
    text: str = "",
):
    """Create a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.text = text
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    return resp


def _mock_client(response):
    """Create a mock httpx.AsyncClient context manager."""
    client = AsyncMock()
    client.get = AsyncMock(return_value=response)
    client.post = AsyncMock(return_value=response)
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=client)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


# ---------------------------------------------------------------------------
# Grants.gov
# ---------------------------------------------------------------------------


class TestGrantsGovProvider:
    @pytest.mark.asyncio
    async def test_search_success(self):
        from app.services.data_providers.grants_gov import GrantsGovProvider

        provider = GrantsGovProvider()
        response_data = {
            "oppHits": [
                {
                    "id": "12345",
                    "title": "Cybersecurity Grant",
                    "agencyName": "DHS",
                    "synopsis": "Grant for cyber services",
                    "openDate": "2025-01-01",
                    "closeDate": "2025-03-01",
                    "awardCeiling": "500000",
                    "cfdaNumber": "97.156",
                }
            ]
        }
        mock_resp = _mock_httpx_response(json_data=response_data)
        mock_cm = _mock_client(mock_resp)

        with patch(
            "app.services.data_providers.grants_gov.httpx.AsyncClient", return_value=mock_cm
        ):
            results = await provider.search(SearchParams(keywords="cybersecurity"))

        assert len(results) == 1
        assert isinstance(results[0], RawOpportunity)
        assert results[0].external_id == "12345"
        assert results[0].title == "Cybersecurity Grant"
        assert results[0].source_type == "grants_gov"
        assert results[0].estimated_value == 500000.0

    @pytest.mark.asyncio
    async def test_search_with_naics(self):
        from app.services.data_providers.grants_gov import GrantsGovProvider

        provider = GrantsGovProvider()
        mock_resp = _mock_httpx_response(json_data={"oppHits": []})
        mock_cm = _mock_client(mock_resp)

        with patch(
            "app.services.data_providers.grants_gov.httpx.AsyncClient", return_value=mock_cm
        ):
            results = await provider.search(
                SearchParams(keywords="cyber", naics_codes=["541512", "541519"])
            )

        assert results == []

    @pytest.mark.asyncio
    async def test_search_http_error(self):
        from app.services.data_providers.grants_gov import GrantsGovProvider

        provider = GrantsGovProvider()
        mock_resp = _mock_httpx_response(status_code=500)
        mock_cm = _mock_client(mock_resp)

        with patch(
            "app.services.data_providers.grants_gov.httpx.AsyncClient", return_value=mock_cm
        ):
            results = await provider.search(SearchParams(keywords="test"))

        assert results == []

    @pytest.mark.asyncio
    async def test_get_details_success(self):
        from app.services.data_providers.grants_gov import GrantsGovProvider

        provider = GrantsGovProvider()
        detail_data = {
            "oppId": "99999",
            "oppTitle": "Detail Grant",
            "agency": "DOE",
        }
        mock_resp = _mock_httpx_response(json_data=detail_data)
        mock_cm = _mock_client(mock_resp)

        with patch(
            "app.services.data_providers.grants_gov.httpx.AsyncClient", return_value=mock_cm
        ):
            result = await provider.get_details("99999")

        assert result is not None
        assert result.title == "Detail Grant"

    @pytest.mark.asyncio
    async def test_get_details_http_error(self):
        from app.services.data_providers.grants_gov import GrantsGovProvider

        provider = GrantsGovProvider()
        mock_resp = _mock_httpx_response(status_code=500)
        mock_cm = _mock_client(mock_resp)

        with patch(
            "app.services.data_providers.grants_gov.httpx.AsyncClient", return_value=mock_cm
        ):
            result = await provider.get_details("99999")

        assert result is None

    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        from app.services.data_providers.grants_gov import GrantsGovProvider

        provider = GrantsGovProvider()
        mock_resp = _mock_httpx_response(status_code=200)
        mock_cm = _mock_client(mock_resp)

        with patch(
            "app.services.data_providers.grants_gov.httpx.AsyncClient", return_value=mock_cm
        ):
            assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self):
        from app.services.data_providers.grants_gov import GrantsGovProvider

        provider = GrantsGovProvider()
        mock_resp = _mock_httpx_response(status_code=503)
        mock_cm = _mock_client(mock_resp)

        with patch(
            "app.services.data_providers.grants_gov.httpx.AsyncClient", return_value=mock_cm
        ):
            assert await provider.health_check() is False


# ---------------------------------------------------------------------------
# USAspending
# ---------------------------------------------------------------------------


class TestUSAspendingProvider:
    @pytest.mark.asyncio
    async def test_search_success(self):
        from app.services.data_providers.usaspending import USAspendingProvider

        provider = USAspendingProvider()
        response_data = {
            "results": [
                {
                    "generated_internal_id": "USA-001",
                    "Description": "IT Support Services",
                    "Awarding Agency": "DoD",
                    "Start Date": "2025-01-15",
                    "Award Amount": 1500000,
                    "NAICS Code": "541512",
                }
            ]
        }
        mock_resp = _mock_httpx_response(json_data=response_data)
        mock_cm = _mock_client(mock_resp)

        with patch(
            "app.services.data_providers.usaspending.httpx.AsyncClient",
            return_value=mock_cm,
        ):
            results = await provider.search(SearchParams(keywords="IT"))

        assert len(results) == 1
        assert results[0].external_id == "USA-001"
        assert results[0].estimated_value == 1500000.0
        assert results[0].source_type == "usaspending"

    @pytest.mark.asyncio
    async def test_search_with_all_filters(self):
        from app.services.data_providers.usaspending import USAspendingProvider

        provider = USAspendingProvider()
        mock_resp = _mock_httpx_response(json_data={"results": []})
        mock_cm = _mock_client(mock_resp)

        with patch(
            "app.services.data_providers.usaspending.httpx.AsyncClient",
            return_value=mock_cm,
        ):
            results = await provider.search(
                SearchParams(keywords="cyber", naics_codes=["541512"], agency="DoD", days_back=30)
            )

        assert results == []

    @pytest.mark.asyncio
    async def test_search_http_error(self):
        from app.services.data_providers.usaspending import USAspendingProvider

        provider = USAspendingProvider()
        mock_resp = _mock_httpx_response(status_code=500)
        mock_cm = _mock_client(mock_resp)

        with patch(
            "app.services.data_providers.usaspending.httpx.AsyncClient",
            return_value=mock_cm,
        ):
            results = await provider.search(SearchParams(keywords="test"))

        assert results == []

    @pytest.mark.asyncio
    async def test_get_details_success(self):
        from app.services.data_providers.usaspending import USAspendingProvider

        provider = USAspendingProvider()
        detail = {
            "generated_unique_award_id": "AWARD-123",
            "description": "Detailed award",
            "total_obligation": "2500000",
            "awarding_agency": {"toptier_agency": {"name": "NASA"}},
            "naics": {"code": "541330"},
            "period_of_performance_start_date": "2025-02-01",
        }
        mock_resp = _mock_httpx_response(json_data=detail)
        mock_cm = _mock_client(mock_resp)

        with patch(
            "app.services.data_providers.usaspending.httpx.AsyncClient",
            return_value=mock_cm,
        ):
            result = await provider.get_details("AWARD-123")

        assert result is not None
        assert result.external_id == "AWARD-123"
        assert result.agency == "NASA"
        assert result.estimated_value == 2500000.0

    @pytest.mark.asyncio
    async def test_get_details_empty_response(self):
        from app.services.data_providers.usaspending import USAspendingProvider

        provider = USAspendingProvider()
        mock_resp = _mock_httpx_response(json_data={})
        mock_cm = _mock_client(mock_resp)

        with patch(
            "app.services.data_providers.usaspending.httpx.AsyncClient",
            return_value=mock_cm,
        ):
            # Empty dict is falsy — should return None
            result = await provider.get_details("MISSING")

        assert result is None

    @pytest.mark.asyncio
    async def test_health_check(self):
        from app.services.data_providers.usaspending import USAspendingProvider

        provider = USAspendingProvider()
        mock_resp = _mock_httpx_response(status_code=200)
        mock_cm = _mock_client(mock_resp)

        with patch(
            "app.services.data_providers.usaspending.httpx.AsyncClient",
            return_value=mock_cm,
        ):
            assert await provider.health_check() is True


# ---------------------------------------------------------------------------
# FPDS
# ---------------------------------------------------------------------------


class TestFPDSProvider:
    SAMPLE_ATOM_XML = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom" xmlns:ns1="https://www.fpds.gov/FPDS">
      <entry>
        <title>Test Contract Award</title>
        <id>urn:fpds:entry:1</id>
        <link href="https://fpds.gov/award/1"/>
        <content>
          <ns1:award>
            <ns1:awardID>
              <ns1:awardContractID>
                <ns1:PIID>FA8721-24-C-0001</ns1:PIID>
              </ns1:awardContractID>
            </ns1:awardID>
            <ns1:contractData>
              <ns1:descriptionOfContractRequirement>IT services</ns1:descriptionOfContractRequirement>
            </ns1:contractData>
            <ns1:competition>
              <ns1:NAICSCode>541512</ns1:NAICSCode>
            </ns1:competition>
            <ns1:dollarValues>
              <ns1:obligatedAmount>750000</ns1:obligatedAmount>
            </ns1:dollarValues>
            <ns1:purchaserInformation>
              <ns1:contractingOfficeAgencyID name="Air Force">AF</ns1:contractingOfficeAgencyID>
            </ns1:purchaserInformation>
          </ns1:award>
        </content>
      </entry>
    </feed>"""

    @pytest.mark.asyncio
    async def test_search_success(self):
        from app.services.data_providers.fpds import FPDSProvider

        provider = FPDSProvider()
        mock_resp = _mock_httpx_response(text=self.SAMPLE_ATOM_XML)
        mock_cm = _mock_client(mock_resp)

        with patch("app.services.data_providers.fpds.httpx.AsyncClient", return_value=mock_cm):
            results = await provider.search(SearchParams(keywords="IT"))

        assert len(results) == 1
        assert results[0].external_id == "FA8721-24-C-0001"
        assert results[0].naics_code == "541512"
        assert results[0].estimated_value == 750000.0
        assert results[0].source_type == "fpds"
        assert results[0].agency == "Air Force"

    @pytest.mark.asyncio
    async def test_search_with_filters(self):
        from app.services.data_providers.fpds import FPDSProvider

        provider = FPDSProvider()
        mock_resp = _mock_httpx_response(text=self.SAMPLE_ATOM_XML)
        mock_cm = _mock_client(mock_resp)

        with patch("app.services.data_providers.fpds.httpx.AsyncClient", return_value=mock_cm):
            results = await provider.search(
                SearchParams(keywords="IT", naics_codes=["541512"], agency="DoD")
            )

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_empty_feed(self):
        from app.services.data_providers.fpds import FPDSProvider

        provider = FPDSProvider()
        empty_xml = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'
        mock_resp = _mock_httpx_response(text=empty_xml)
        mock_cm = _mock_client(mock_resp)

        with patch("app.services.data_providers.fpds.httpx.AsyncClient", return_value=mock_cm):
            results = await provider.search(SearchParams(keywords="nonexistent"))

        assert results == []

    @pytest.mark.asyncio
    async def test_search_invalid_xml(self):
        from app.services.data_providers.fpds import FPDSProvider

        provider = FPDSProvider()
        mock_resp = _mock_httpx_response(text="not xml at all")
        mock_cm = _mock_client(mock_resp)

        with patch("app.services.data_providers.fpds.httpx.AsyncClient", return_value=mock_cm):
            results = await provider.search(SearchParams())

        assert results == []

    @pytest.mark.asyncio
    async def test_search_http_error(self):
        from app.services.data_providers.fpds import FPDSProvider

        provider = FPDSProvider()
        mock_resp = _mock_httpx_response(status_code=500)
        mock_cm = _mock_client(mock_resp)

        with patch("app.services.data_providers.fpds.httpx.AsyncClient", return_value=mock_cm):
            results = await provider.search(SearchParams())

        assert results == []

    @pytest.mark.asyncio
    async def test_get_details_success(self):
        from app.services.data_providers.fpds import FPDSProvider

        provider = FPDSProvider()
        mock_resp = _mock_httpx_response(text=self.SAMPLE_ATOM_XML)
        mock_cm = _mock_client(mock_resp)

        with patch("app.services.data_providers.fpds.httpx.AsyncClient", return_value=mock_cm):
            result = await provider.get_details("FA8721-24-C-0001")

        assert result is not None
        assert result.external_id == "FA8721-24-C-0001"

    @pytest.mark.asyncio
    async def test_health_check(self):
        from app.services.data_providers.fpds import FPDSProvider

        provider = FPDSProvider()
        mock_resp = _mock_httpx_response(status_code=200)
        mock_cm = _mock_client(mock_resp)

        with patch("app.services.data_providers.fpds.httpx.AsyncClient", return_value=mock_cm):
            assert await provider.health_check() is True


# ---------------------------------------------------------------------------
# SEWP
# ---------------------------------------------------------------------------


class TestSEWPProvider:
    @pytest.mark.asyncio
    async def test_search_success(self):
        from app.services.data_providers.sewp import SEWPProvider

        provider = SEWPProvider()
        response_data = {
            "results": [
                {
                    "rfqNumber": "SEWP-001",
                    "title": "IT Hardware",
                    "agency": "NASA",
                    "postedDate": "2025-01-10",
                    "closeDate": "2025-02-10",
                    "naicsCode": "334111",
                }
            ]
        }
        mock_resp = _mock_httpx_response(json_data=response_data)
        mock_cm = _mock_client(mock_resp)

        with patch("app.services.data_providers.sewp.httpx.AsyncClient", return_value=mock_cm):
            results = await provider.search(SearchParams(keywords="hardware"))

        assert len(results) == 1
        assert results[0].external_id == "SEWP-001"
        assert results[0].source_type == "sewp"

    @pytest.mark.asyncio
    async def test_search_http_error(self):
        from app.services.data_providers.sewp import SEWPProvider

        provider = SEWPProvider()
        mock_resp = _mock_httpx_response(status_code=500)
        mock_cm = _mock_client(mock_resp)

        with patch("app.services.data_providers.sewp.httpx.AsyncClient", return_value=mock_cm):
            results = await provider.search(SearchParams())

        assert results == []

    @pytest.mark.asyncio
    async def test_get_details_success(self):
        from app.services.data_providers.sewp import SEWPProvider

        provider = SEWPProvider()
        detail = {
            "rfqNumber": "SEWP-002",
            "title": "Server Purchase",
            "description": "Buy 50 servers",
        }
        mock_resp = _mock_httpx_response(json_data=detail)
        mock_cm = _mock_client(mock_resp)

        with patch("app.services.data_providers.sewp.httpx.AsyncClient", return_value=mock_cm):
            result = await provider.get_details("SEWP-002")

        assert result is not None
        assert result.title == "Server Purchase"

    @pytest.mark.asyncio
    async def test_get_details_http_error(self):
        from app.services.data_providers.sewp import SEWPProvider

        provider = SEWPProvider()
        mock_resp = _mock_httpx_response(status_code=500)
        mock_cm = _mock_client(mock_resp)

        with patch("app.services.data_providers.sewp.httpx.AsyncClient", return_value=mock_cm):
            result = await provider.get_details("MISSING")

        assert result is None

    @pytest.mark.asyncio
    async def test_health_check(self):
        from app.services.data_providers.sewp import SEWPProvider

        provider = SEWPProvider()
        mock_resp = _mock_httpx_response(status_code=200)
        mock_cm = _mock_client(mock_resp)

        with patch("app.services.data_providers.sewp.httpx.AsyncClient", return_value=mock_cm):
            assert await provider.health_check() is True


# ---------------------------------------------------------------------------
# GSA eBuy
# ---------------------------------------------------------------------------


class TestGSAEbuyProvider:
    @pytest.mark.asyncio
    async def test_search_no_api_key(self):
        from app.services.data_providers.gsa_ebuy import GSAEbuyProvider

        provider = GSAEbuyProvider()

        with patch("app.services.data_providers.gsa_ebuy.settings") as mock_settings:
            mock_settings.sam_gov_api_key = None
            results = await provider.search(SearchParams(keywords="test"))

        assert results == []

    @pytest.mark.asyncio
    async def test_search_success(self):
        from app.services.data_providers.gsa_ebuy import GSAEbuyProvider

        provider = GSAEbuyProvider()
        response_data = {
            "opportunitiesData": [
                {
                    "noticeId": "EBUY-001",
                    "title": "Cloud Services RFQ",
                    "postedDate": "2025-01-15",
                    "responseDeadLine": "2025-02-15",
                    "naicsCode": "541519",
                }
            ]
        }
        mock_resp = _mock_httpx_response(json_data=response_data)
        mock_cm = _mock_client(mock_resp)

        with (
            patch("app.services.data_providers.gsa_ebuy.settings") as mock_settings,
            patch("app.services.data_providers.gsa_ebuy.httpx.AsyncClient", return_value=mock_cm),
        ):
            mock_settings.sam_gov_api_key = "test-key"
            results = await provider.search(SearchParams(keywords="cloud"))

        assert len(results) == 1
        assert results[0].external_id == "EBUY-001"
        assert results[0].source_type == "gsa_ebuy"

    @pytest.mark.asyncio
    async def test_get_details_no_api_key(self):
        from app.services.data_providers.gsa_ebuy import GSAEbuyProvider

        provider = GSAEbuyProvider()

        with patch("app.services.data_providers.gsa_ebuy.settings") as mock_settings:
            mock_settings.sam_gov_api_key = None
            result = await provider.get_details("EBUY-001")

        assert result is None

    @pytest.mark.asyncio
    async def test_health_check_no_key(self):
        from app.services.data_providers.gsa_ebuy import GSAEbuyProvider

        provider = GSAEbuyProvider()

        with patch("app.services.data_providers.gsa_ebuy.settings") as mock_settings:
            mock_settings.sam_gov_api_key = None
            assert await provider.health_check() is False

    @pytest.mark.asyncio
    async def test_health_check_with_key(self):
        from app.services.data_providers.gsa_ebuy import GSAEbuyProvider

        provider = GSAEbuyProvider()
        mock_resp = _mock_httpx_response(status_code=200)
        mock_cm = _mock_client(mock_resp)

        with (
            patch("app.services.data_providers.gsa_ebuy.settings") as mock_settings,
            patch("app.services.data_providers.gsa_ebuy.httpx.AsyncClient", return_value=mock_cm),
        ):
            mock_settings.sam_gov_api_key = "test-key"
            assert await provider.health_check() is True
