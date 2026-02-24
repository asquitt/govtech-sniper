"""
Unit tests for remaining data_providers:
  - DIBBS (DLA)
  - SLED BidNet
  - Contract Vehicle Feeds (_SAMVehicleProvider base, mapping)
  - Canada open-data helpers (parsing, filtering, mapping)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.data_providers.base import SearchParams

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_httpx_response(status_code: int = 200, json_data: dict | None = None, text: str = ""):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    return resp


def _mock_client(response):
    client = AsyncMock()
    client.get = AsyncMock(return_value=response)
    client.post = AsyncMock(return_value=response)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


# ===========================================================================
# DIBBS Provider
# ===========================================================================


class TestDIBBSProvider:
    @pytest.mark.asyncio
    @patch("app.services.data_providers.dibbs.httpx.AsyncClient")
    async def test_search_success(self, mock_client_cls):
        from app.services.data_providers.dibbs import DIBBSProvider

        mock_client_cls.return_value = _mock_client(
            _mock_httpx_response(
                json_data={
                    "results": [
                        {
                            "solicitationNumber": "SP4500-24-001",
                            "title": "Bearings Kit",
                            "agency": "DLA",
                            "description": "Bearings procurement",
                        }
                    ]
                }
            )
        )

        provider = DIBBSProvider()
        results = await provider.search(SearchParams(limit=10, keywords="bearings"))
        assert len(results) == 1
        assert results[0].external_id == "DIBBS-SP4500-24-001"
        assert results[0].source_type == "dibbs"

    @pytest.mark.asyncio
    @patch("app.services.data_providers.dibbs.httpx.AsyncClient")
    async def test_search_error(self, mock_client_cls):
        from app.services.data_providers.dibbs import DIBBSProvider

        mock_client_cls.return_value = _mock_client(_mock_httpx_response(status_code=500))
        provider = DIBBSProvider()
        results = await provider.search(SearchParams(limit=10, keywords="test"))
        assert results == []

    @pytest.mark.asyncio
    @patch("app.services.data_providers.dibbs.httpx.AsyncClient")
    async def test_get_details_success(self, mock_client_cls):
        from app.services.data_providers.dibbs import DIBBSProvider

        mock_client_cls.return_value = _mock_client(
            _mock_httpx_response(
                json_data={
                    "solicitationNumber": "SP4500-24-002",
                    "title": "Test Item",
                }
            )
        )
        provider = DIBBSProvider()
        result = await provider.get_details("SP4500-24-002")
        assert result is not None
        assert result.external_id == "DIBBS-SP4500-24-002"

    @pytest.mark.asyncio
    @patch("app.services.data_providers.dibbs.httpx.AsyncClient")
    async def test_health_check(self, mock_client_cls):
        from app.services.data_providers.dibbs import DIBBSProvider

        mock_client_cls.return_value = _mock_client(_mock_httpx_response(200))
        provider = DIBBSProvider()
        assert await provider.health_check() is True


# ===========================================================================
# SLED BidNet Provider
# ===========================================================================


class TestSLEDBidNetProvider:
    @pytest.mark.asyncio
    @patch("app.services.data_providers.sled_bidnet.httpx.AsyncClient")
    async def test_search_success(self, mock_client_cls):
        from app.services.data_providers.sled_bidnet import SLEDBidNetProvider

        mock_client_cls.return_value = _mock_client(
            _mock_httpx_response(
                json_data={
                    "solicitations": [
                        {
                            "solicitationId": "12345",
                            "title": "IT Services",
                            "buyerName": "City of Austin",
                        }
                    ]
                }
            )
        )
        provider = SLEDBidNetProvider()
        results = await provider.search(SearchParams(limit=10, keywords="IT"))
        assert len(results) == 1
        assert results[0].external_id == "SLED-12345"
        assert results[0].source_type == "sled"

    @pytest.mark.asyncio
    @patch("app.services.data_providers.sled_bidnet.httpx.AsyncClient")
    async def test_search_error(self, mock_client_cls):
        from app.services.data_providers.sled_bidnet import SLEDBidNetProvider

        mock_client_cls.return_value = _mock_client(_mock_httpx_response(status_code=503))
        provider = SLEDBidNetProvider()
        results = await provider.search(SearchParams(limit=10))
        assert results == []

    @pytest.mark.asyncio
    @patch("app.services.data_providers.sled_bidnet.httpx.AsyncClient")
    async def test_health_check_success(self, mock_client_cls):
        from app.services.data_providers.sled_bidnet import SLEDBidNetProvider

        mock_client_cls.return_value = _mock_client(_mock_httpx_response(200))
        provider = SLEDBidNetProvider()
        assert await provider.health_check() is True


# ===========================================================================
# Contract Vehicle Feed Helpers
# ===========================================================================


class TestContractVehicleMapping:
    def test_map_sam_to_raw(self):
        from app.services.data_providers.contract_vehicle_feeds import _map_sam_to_raw

        opp = {
            "noticeId": "NOTICE-123",
            "title": "CIO-SP3 Task Order",
            "fullParentPathName": "HHS / NIH",
            "description": "Cloud services task order",
            "postedDate": "2025-01-15",
            "naicsCode": "541512",
        }
        result = _map_sam_to_raw(opp, "cio_sp3")
        assert result.external_id == "NOTICE-123"
        assert result.source_type == "cio_sp3"
        assert result.naics_code == "541512"

    def test_days_back_date(self):
        from app.services.data_providers.contract_vehicle_feeds import _days_back_date

        result = _days_back_date(30)
        assert "/" in result  # MM/DD/YYYY format

    def test_today(self):
        from app.services.data_providers.contract_vehicle_feeds import _today

        result = _today()
        assert "/" in result


class TestContractVehicleProviders:
    @pytest.mark.asyncio
    @patch("app.services.data_providers.contract_vehicle_feeds.httpx.AsyncClient")
    async def test_search_no_api_key(self, mock_client_cls):
        from app.services.data_providers.contract_vehicle_feeds import GsaMasProvider

        with patch("app.services.data_providers.contract_vehicle_feeds.settings") as mock_settings:
            mock_settings.sam_gov_api_key = None
            provider = GsaMasProvider()
            results = await provider.search(SearchParams(limit=10))
            assert results == []

    @pytest.mark.asyncio
    @patch("app.services.data_providers.contract_vehicle_feeds.httpx.AsyncClient")
    async def test_search_success(self, mock_client_cls):
        from app.services.data_providers.contract_vehicle_feeds import GsaMasProvider

        mock_client_cls.return_value = _mock_client(
            _mock_httpx_response(
                json_data={
                    "opportunitiesData": [
                        {
                            "noticeId": "GSA-001",
                            "title": "GSA Schedule Task",
                            "naicsCode": "541512",
                        }
                    ]
                }
            )
        )
        with patch("app.services.data_providers.contract_vehicle_feeds.settings") as mock_settings:
            mock_settings.sam_gov_api_key = "test-key"
            provider = GsaMasProvider()
            results = await provider.search(SearchParams(limit=10))
            assert len(results) == 1
            assert results[0].source_type == "gsa_mas"

    @pytest.mark.asyncio
    @patch("app.services.data_providers.contract_vehicle_feeds.httpx.AsyncClient")
    async def test_health_no_api_key(self, mock_client_cls):
        from app.services.data_providers.contract_vehicle_feeds import OasisProvider

        with patch("app.services.data_providers.contract_vehicle_feeds.settings") as mock_settings:
            mock_settings.sam_gov_api_key = None
            provider = OasisProvider()
            assert await provider.health_check() is False


# ===========================================================================
# Canada Open Data Helpers (pure functions)
# ===========================================================================


class TestCanadaOpenDataParsing:
    def test_parse_datetime_iso(self):
        from app.services.data_providers.canada_open_data import _parse_datetime

        result = _parse_datetime("2025-06-15T10:00:00")
        assert result is not None
        assert result.year == 2025
        assert result.month == 6

    def test_parse_datetime_date_only(self):
        from app.services.data_providers.canada_open_data import _parse_datetime

        result = _parse_datetime("2025-06-15")
        assert result is not None
        assert result.day == 15

    def test_parse_datetime_with_z(self):
        from app.services.data_providers.canada_open_data import _parse_datetime

        result = _parse_datetime("2025-06-15T10:00:00Z")
        assert result is not None

    def test_parse_datetime_none(self):
        from app.services.data_providers.canada_open_data import _parse_datetime

        assert _parse_datetime(None) is None
        assert _parse_datetime("") is None
        assert _parse_datetime("   ") is None

    def test_parse_datetime_invalid(self):
        from app.services.data_providers.canada_open_data import _parse_datetime

        assert _parse_datetime("not-a-date") is None


class TestCanadaRegionNormalization:
    def test_normalize_known_province(self):
        from app.services.data_providers.canada_open_data import _normalize_region_token

        assert _normalize_region_token("ON") == "ON"
        assert _normalize_region_token("Ontario") == "ON"
        assert _normalize_region_token("BRITISH COLUMBIA") == "BC"
        assert _normalize_region_token("Québec") == "QC"

    def test_normalize_unknown(self):
        from app.services.data_providers.canada_open_data import _normalize_region_token

        assert _normalize_region_token("XYZ") is None

    def test_normalize_none(self):
        from app.services.data_providers.canada_open_data import _normalize_region_token

        assert _normalize_region_token(None) is None
        assert _normalize_region_token("") is None


class TestCanadaExternalId:
    def test_with_reference(self):
        from app.services.data_providers.canada_open_data import _build_external_id

        row = {
            "referenceNumber-numeroReference": "PW-24-001",
            "solicitationNumber-numeroSollicitation": "SOL-001",
        }
        result = _build_external_id(row)
        assert result == "CA-PW-24-001"

    def test_fallback_to_solicitation(self):
        from app.services.data_providers.canada_open_data import _build_external_id

        row = {
            "referenceNumber-numeroReference": "",
            "solicitationNumber-numeroSollicitation": "SOL-002",
        }
        result = _build_external_id(row)
        assert result == "CA-SOL-002"

    def test_fallback_to_hash(self):
        from app.services.data_providers.canada_open_data import _build_external_id

        row = {"referenceNumber-numeroReference": "", "solicitationNumber-numeroSollicitation": ""}
        result = _build_external_id(row)
        assert result.startswith("CA-CAN-")


class TestCanadaRowToOpportunity:
    def test_basic_mapping(self):
        from app.services.data_providers.canada_open_data import row_to_opportunity

        row = {
            "referenceNumber-numeroReference": "REF-001",
            "solicitationNumber-numeroSollicitation": "",
            "title-titre-eng": "IT Modernization Project",
            "title-titre-fra": "",
            "contractingEntityName-nomEntitContractante-eng": "Shared Services Canada",
            "tenderDescription-descriptionAppelOffres-eng": "Modernize legacy systems.",
            "publicationDate-datePublication": "2025-01-15",
            "tenderClosingDate-appelOffresDateCloture": "2025-03-01",
            "gsin-nibs": "N70",
            "unspsc": "",
            "noticeURL-URLavis-eng": "https://canadabuys.canada.ca/notice/123",
            "contractingEntityAddressProvince-entiteContractanteAdresseProvince-eng": "Ontario",
            "regionsOfOpportunity-regionAppelOffres-eng": "",
            "regionsOfDelivery-regionsLivraison-eng": "",
            "tenderStatus-appelOffresStatut-eng": "",
        }
        result = row_to_opportunity(
            row, source_type="canada_buyandsell", include_portal_metadata=False
        )
        assert result.external_id == "CA-REF-001"
        assert result.title == "IT Modernization Project"
        assert result.agency == "Shared Services Canada"
        assert result.currency == "CAD"
        assert result.source_type == "canada_buyandsell"


class TestCanadaCsvParsing:
    def test_iter_csv_rows(self):
        from app.services.data_providers.canada_open_data import _iter_csv_rows

        csv_text = "col1,col2\nval1,val2\nval3,val4\n"
        rows = _iter_csv_rows(csv_text)
        assert len(rows) == 2
        assert rows[0]["col1"] == "val1"
        assert rows[1]["col2"] == "val4"

    def test_iter_csv_with_bom(self):
        from app.services.data_providers.canada_open_data import _iter_csv_rows

        csv_text = "\ufeffcol1,col2\nval1,val2\n"
        rows = _iter_csv_rows(csv_text)
        assert len(rows) == 1
        assert "col1" in rows[0]


class TestCanadaNaicsNormalization:
    def test_normalize_naics_codes(self):
        from app.services.data_providers.canada_open_data import _normalize_naics_codes

        result = _normalize_naics_codes(["541512", "N70-abc"])
        assert "541512" in result
        assert "70" in result

    def test_normalize_empty(self):
        from app.services.data_providers.canada_open_data import _normalize_naics_codes

        assert _normalize_naics_codes(None) == set()
        assert _normalize_naics_codes([]) == set()
