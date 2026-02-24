"""
Ingest Service (SAM.gov) Unit Tests
=====================================
Tests for pure/synchronous helpers: _parse_opportunity, PTYPE_MAP, SAMGovAPIError,
mock helpers, and circuit breaker logic.
"""

from datetime import datetime, timedelta
from unittest.mock import patch

from app.models.rfp import RFPType
from app.services.ingest_service import SAMGovAPIError, SAMGovService

# ---------------------------------------------------------------------------
# SAMGovAPIError
# ---------------------------------------------------------------------------


class TestSAMGovAPIError:
    def test_basic(self):
        err = SAMGovAPIError("test error")
        assert str(err) == "test error"
        assert err.status_code is None
        assert err.retryable is True

    def test_with_status(self):
        err = SAMGovAPIError("rate limited", status_code=429, retryable=False, is_rate_limited=True)
        assert err.status_code == 429
        assert err.retryable is False
        assert err.is_rate_limited is True

    def test_retry_after(self):
        err = SAMGovAPIError("retry", retry_after_seconds=60)
        assert err.retry_after_seconds == 60


# ---------------------------------------------------------------------------
# PTYPE_MAP
# ---------------------------------------------------------------------------


class TestPtypeMap:
    def test_known_types(self):
        svc = SAMGovService(api_key="test", mock_variant="v1")
        assert svc.PTYPE_MAP["o"] == RFPType.SOLICITATION
        assert svc.PTYPE_MAP["p"] == RFPType.PRESOLICITATION
        assert svc.PTYPE_MAP["k"] == RFPType.COMBINED
        assert svc.PTYPE_MAP["r"] == RFPType.SOURCES_SOUGHT
        assert svc.PTYPE_MAP["s"] == RFPType.SPECIAL_NOTICE
        assert svc.PTYPE_MAP["a"] == RFPType.AWARD


# ---------------------------------------------------------------------------
# _parse_opportunity
# ---------------------------------------------------------------------------


class TestParseOpportunity:
    def _make_service(self):
        with patch("app.services.ingest_service.settings") as mock_settings:
            mock_settings.sam_gov_api_key = "test-key"
            mock_settings.sam_gov_base_url = "https://api.sam.gov/prod/opportunities/v2/search"
            mock_settings.mock_sam_gov = False
            mock_settings.mock_sam_gov_variant = "v1"
            mock_settings.sam_circuit_breaker_enabled = False
            return SAMGovService(api_key="test-key")

    def test_basic_parsing(self):
        svc = self._make_service()
        raw = {
            "title": "IT Modernization",
            "solicitationNumber": "SOL-001",
            "organizationHierarchy": [
                {"name": "Department of Defense"},
                {"name": "DISA"},
            ],
            "postedDate": "2025-01-15",
            "responseDeadLine": "2025-03-01",
            "naicsCode": "541512",
            "typeOfSetAsideDescription": "Total Small Business",
            "type": "o",
            "uiLink": "https://sam.gov/opp/123",
            "description": "Test description",
        }
        opp = svc.parse_opportunity(raw)
        assert opp.title == "IT Modernization"
        assert opp.solicitation_number == "SOL-001"
        assert opp.agency == "Department of Defense"
        assert opp.sub_agency == "DISA"
        assert opp.naics_code == "541512"
        assert opp.rfp_type == RFPType.SOLICITATION
        assert opp.posted_date.year == 2025
        assert opp.response_deadline.month == 3

    def test_missing_org_hierarchy(self):
        svc = self._make_service()
        raw = {
            "title": "Test",
            "organizationHierarchy": [],
            "type": "o",
        }
        opp = svc.parse_opportunity(raw)
        assert opp.agency == "Unknown"
        assert opp.sub_agency is None

    def test_single_org(self):
        svc = self._make_service()
        raw = {
            "title": "Test",
            "organizationHierarchy": [{"name": "GSA"}],
            "type": "k",
        }
        opp = svc.parse_opportunity(raw)
        assert opp.agency == "GSA"
        assert opp.sub_agency is None
        assert opp.rfp_type == RFPType.COMBINED

    def test_invalid_date(self):
        svc = self._make_service()
        raw = {
            "title": "Test",
            "organizationHierarchy": [],
            "postedDate": "not-a-date",
            "responseDeadLine": "also-bad",
            "type": "o",
        }
        opp = svc.parse_opportunity(raw)
        assert opp.posted_date is None
        assert opp.response_deadline is None

    def test_no_date_fields(self):
        svc = self._make_service()
        raw = {"title": "Test", "organizationHierarchy": [], "type": "r"}
        opp = svc.parse_opportunity(raw)
        assert opp.posted_date is None
        assert opp.response_deadline is None
        assert opp.rfp_type == RFPType.SOURCES_SOUGHT

    def test_unknown_ptype_defaults_to_solicitation(self):
        svc = self._make_service()
        raw = {"title": "Test", "organizationHierarchy": [], "type": "z"}
        opp = svc.parse_opportunity(raw)
        assert opp.rfp_type == RFPType.SOLICITATION

    def test_fallback_notice_id(self):
        svc = self._make_service()
        raw = {
            "title": "Test",
            "organizationHierarchy": [],
            "noticeId": "NOTICE-999",
            "type": "o",
        }
        opp = svc.parse_opportunity(raw)
        assert opp.solicitation_number == "NOTICE-999"


# ---------------------------------------------------------------------------
# Mock mode
# ---------------------------------------------------------------------------


class TestMockMode:
    def test_mock_raw_opportunities(self):
        with patch("app.services.ingest_service.settings") as mock_settings:
            mock_settings.sam_gov_api_key = None
            mock_settings.sam_gov_base_url = ""
            mock_settings.mock_sam_gov = True
            mock_settings.mock_sam_gov_variant = "v1"
            mock_settings.sam_circuit_breaker_enabled = False

            from app.schemas.rfp import SAMSearchParams

            svc = SAMGovService(mock_variant="v1")
            params = SAMSearchParams(keywords="cloud", limit=3)
            raw = svc._mock_raw_opportunities(params)
            assert len(raw) == 3
            assert raw[0]["noticeId"] == "MOCK-SAM-001"
            assert "cloud" in raw[0]["title"].lower()

    def test_mock_opportunities_parsed(self):
        with patch("app.services.ingest_service.settings") as mock_settings:
            mock_settings.sam_gov_api_key = None
            mock_settings.sam_gov_base_url = ""
            mock_settings.mock_sam_gov = True
            mock_settings.mock_sam_gov_variant = "v1"
            mock_settings.sam_circuit_breaker_enabled = False

            from app.schemas.rfp import SAMSearchParams

            svc = SAMGovService(mock_variant="v1")
            params = SAMSearchParams(keywords="security", limit=2)
            opps = svc._mock_opportunities(params)
            assert len(opps) == 2
            assert opps[0].solicitation_number == "MOCK-SAM-001"
            assert opps[1].rfp_type == RFPType.COMBINED


# ---------------------------------------------------------------------------
# Circuit breaker (class-level state)
# ---------------------------------------------------------------------------


class TestCircuitBreaker:
    def setup_method(self):
        # Reset class-level circuit state
        SAMGovService._circuit_open_until = None
        SAMGovService._circuit_reason = None

    def test_circuit_closed_by_default(self):
        with patch("app.services.ingest_service.settings") as mock_settings:
            mock_settings.sam_circuit_breaker_enabled = True
            mock_settings.sam_gov_api_key = "test"
            mock_settings.sam_gov_base_url = ""
            mock_settings.mock_sam_gov = False
            mock_settings.mock_sam_gov_variant = "v1"
            svc = SAMGovService(api_key="test")
            assert svc._is_circuit_open() is False

    def test_circuit_open_after_set(self):
        with patch("app.services.ingest_service.settings") as mock_settings:
            mock_settings.sam_circuit_breaker_enabled = True
            mock_settings.sam_circuit_breaker_cooldown_seconds = 60
            mock_settings.sam_circuit_breaker_max_seconds = 300
            mock_settings.sam_gov_api_key = "test"
            mock_settings.sam_gov_base_url = ""
            mock_settings.mock_sam_gov = False
            mock_settings.mock_sam_gov_variant = "v1"
            svc = SAMGovService(api_key="test")
            svc._open_circuit(retry_after=30, reason="rate_limited")
            assert svc._is_circuit_open() is True
            assert SAMGovService._circuit_reason == "rate_limited"

    def test_circuit_disabled(self):
        with patch("app.services.ingest_service.settings") as mock_settings:
            mock_settings.sam_circuit_breaker_enabled = False
            mock_settings.sam_gov_api_key = "test"
            mock_settings.sam_gov_base_url = ""
            mock_settings.mock_sam_gov = False
            mock_settings.mock_sam_gov_variant = "v1"
            svc = SAMGovService(api_key="test")
            # Even if we set circuit manually, disabled means closed
            SAMGovService._circuit_open_until = datetime.utcnow() + timedelta(seconds=60)
            assert svc._is_circuit_open() is False


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


class TestSAMGovServiceInit:
    def test_api_key_from_param(self):
        with patch("app.services.ingest_service.settings") as mock_settings:
            mock_settings.sam_gov_api_key = "settings-key"
            mock_settings.sam_gov_base_url = "https://api.sam.gov"
            mock_settings.mock_sam_gov = False
            mock_settings.mock_sam_gov_variant = "v1"
            mock_settings.sam_circuit_breaker_enabled = False
            svc = SAMGovService(api_key="custom-key")
            assert svc.api_key == "custom-key"

    def test_api_key_from_settings(self):
        with patch("app.services.ingest_service.settings") as mock_settings:
            mock_settings.sam_gov_api_key = "settings-key"
            mock_settings.sam_gov_base_url = "https://api.sam.gov"
            mock_settings.mock_sam_gov = False
            mock_settings.mock_sam_gov_variant = "v1"
            mock_settings.sam_circuit_breaker_enabled = False
            svc = SAMGovService()
            assert svc.api_key == "settings-key"

    def test_validate_api_key_raises(self):
        with patch("app.services.ingest_service.settings") as mock_settings:
            mock_settings.sam_gov_api_key = None
            mock_settings.sam_gov_base_url = ""
            mock_settings.mock_sam_gov = False
            mock_settings.mock_sam_gov_variant = "v1"
            mock_settings.sam_circuit_breaker_enabled = False
            svc = SAMGovService(api_key=None)
            import pytest

            with pytest.raises(SAMGovAPIError, match="not configured"):
                svc._validate_api_key()

    def test_validate_api_key_skipped_in_mock(self):
        with patch("app.services.ingest_service.settings") as mock_settings:
            mock_settings.sam_gov_api_key = None
            mock_settings.sam_gov_base_url = ""
            mock_settings.mock_sam_gov = True
            mock_settings.mock_sam_gov_variant = "v1"
            mock_settings.sam_circuit_breaker_enabled = False
            svc = SAMGovService(api_key=None)
            # Should not raise
            svc._validate_api_key()
