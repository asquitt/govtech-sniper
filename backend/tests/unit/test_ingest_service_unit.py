"""
Ingest Service Unit Tests
==========================
Tests for SAMGovService parsing, type mapping, and error logic — no HTTP calls.
"""

from datetime import datetime, timedelta
from unittest.mock import patch

from app.models.rfp import RFPType
from app.schemas.rfp import SAMOpportunity, SAMSearchParams
from app.services.ingest_service import SAMGovAPIError, SAMGovService

# =============================================================================
# Fixtures
# =============================================================================


def make_service(mock: bool = True) -> SAMGovService:
    return SAMGovService(api_key="test-key", mock_variant="v1")


def minimal_raw() -> dict:
    return {
        "noticeId": "N-001",
        "solicitationNumber": "SOL-001",
        "title": "Test Opportunity",
        "organizationHierarchy": [{"name": "Dept of Defense"}],
        "postedDate": "2025-01-15",
        "responseDeadLine": "2025-03-01",
        "naicsCode": "541512",
        "typeOfSetAsideDescription": "Total Small Business",
        "type": "o",
        "uiLink": "https://sam.gov/opp/N-001",
        "description": "A test solicitation.",
    }


# =============================================================================
# _parse_opportunity — field extraction
# =============================================================================


class TestParseOpportunityFields:
    def test_title_extracted(self):
        svc = make_service()
        opp = svc._parse_opportunity(minimal_raw())
        assert opp.title == "Test Opportunity"

    def test_solicitation_number_extracted(self):
        svc = make_service()
        opp = svc._parse_opportunity(minimal_raw())
        assert opp.solicitation_number == "SOL-001"

    def test_agency_from_hierarchy_first_element(self):
        svc = make_service()
        opp = svc._parse_opportunity(minimal_raw())
        assert opp.agency == "Dept of Defense"

    def test_sub_agency_from_hierarchy_second_element(self):
        svc = make_service()
        raw = minimal_raw()
        raw["organizationHierarchy"] = [
            {"name": "Dept of Defense"},
            {"name": "Army Corps"},
        ]
        opp = svc._parse_opportunity(raw)
        assert opp.sub_agency == "Army Corps"

    def test_sub_agency_none_when_only_one_element(self):
        svc = make_service()
        opp = svc._parse_opportunity(minimal_raw())
        assert opp.sub_agency is None

    def test_agency_unknown_when_hierarchy_empty(self):
        svc = make_service()
        raw = minimal_raw()
        raw["organizationHierarchy"] = []
        opp = svc._parse_opportunity(raw)
        assert opp.agency == "Unknown"

    def test_naics_code_extracted(self):
        svc = make_service()
        opp = svc._parse_opportunity(minimal_raw())
        assert opp.naics_code == "541512"

    def test_set_aside_extracted(self):
        svc = make_service()
        opp = svc._parse_opportunity(minimal_raw())
        assert opp.set_aside == "Total Small Business"

    def test_ui_link_extracted(self):
        svc = make_service()
        opp = svc._parse_opportunity(minimal_raw())
        assert opp.ui_link == "https://sam.gov/opp/N-001"

    def test_description_extracted(self):
        svc = make_service()
        opp = svc._parse_opportunity(minimal_raw())
        assert opp.description == "A test solicitation."

    def test_title_defaults_to_untitled_when_missing(self):
        svc = make_service()
        raw = minimal_raw()
        del raw["title"]
        opp = svc._parse_opportunity(raw)
        assert opp.title == "Untitled"

    def test_solicitation_number_falls_back_to_notice_id(self):
        svc = make_service()
        raw = minimal_raw()
        del raw["solicitationNumber"]
        opp = svc._parse_opportunity(raw)
        assert opp.solicitation_number == "N-001"

    def test_solicitation_number_unknown_when_both_missing(self):
        svc = make_service()
        raw = minimal_raw()
        del raw["solicitationNumber"]
        del raw["noticeId"]
        opp = svc._parse_opportunity(raw)
        assert opp.solicitation_number == "UNKNOWN"


# =============================================================================
# _parse_opportunity — date parsing
# =============================================================================


class TestDateParsing:
    def test_posted_date_parsed_correctly(self):
        svc = make_service()
        opp = svc._parse_opportunity(minimal_raw())
        assert opp.posted_date == datetime(2025, 1, 15)

    def test_posted_date_none_when_missing(self):
        svc = make_service()
        raw = minimal_raw()
        del raw["postedDate"]
        opp = svc._parse_opportunity(raw)
        assert opp.posted_date is None

    def test_posted_date_none_when_invalid_format(self):
        svc = make_service()
        raw = minimal_raw()
        raw["postedDate"] = "not-a-date"
        opp = svc._parse_opportunity(raw)
        assert opp.posted_date is None

    def test_response_deadline_iso_format(self):
        svc = make_service()
        raw = minimal_raw()
        raw["responseDeadLine"] = "2025-03-01T17:00:00-05:00"
        opp = svc._parse_opportunity(raw)
        assert opp.response_deadline is not None
        assert opp.response_deadline.year == 2025
        assert opp.response_deadline.month == 3

    def test_response_deadline_date_only(self):
        svc = make_service()
        opp = svc._parse_opportunity(minimal_raw())
        assert opp.response_deadline is not None
        assert opp.response_deadline == datetime(2025, 3, 1)

    def test_response_deadline_none_when_missing(self):
        svc = make_service()
        raw = minimal_raw()
        del raw["responseDeadLine"]
        opp = svc._parse_opportunity(raw)
        assert opp.response_deadline is None

    def test_response_deadline_none_when_empty_string(self):
        svc = make_service()
        raw = minimal_raw()
        raw["responseDeadLine"] = ""
        opp = svc._parse_opportunity(raw)
        assert opp.response_deadline is None


# =============================================================================
# _parse_opportunity — RFP type mapping
# =============================================================================


class TestRFPTypeMapping:
    def test_type_o_maps_to_solicitation(self):
        svc = make_service()
        raw = minimal_raw()
        raw["type"] = "o"
        opp = svc._parse_opportunity(raw)
        assert opp.rfp_type == RFPType.SOLICITATION

    def test_type_p_maps_to_presolicitation(self):
        svc = make_service()
        raw = minimal_raw()
        raw["type"] = "p"
        opp = svc._parse_opportunity(raw)
        assert opp.rfp_type == RFPType.PRESOLICITATION

    def test_type_k_maps_to_combined(self):
        svc = make_service()
        raw = minimal_raw()
        raw["type"] = "k"
        opp = svc._parse_opportunity(raw)
        assert opp.rfp_type == RFPType.COMBINED

    def test_type_r_maps_to_sources_sought(self):
        svc = make_service()
        raw = minimal_raw()
        raw["type"] = "r"
        opp = svc._parse_opportunity(raw)
        assert opp.rfp_type == RFPType.SOURCES_SOUGHT

    def test_type_s_maps_to_special_notice(self):
        svc = make_service()
        raw = minimal_raw()
        raw["type"] = "s"
        opp = svc._parse_opportunity(raw)
        assert opp.rfp_type == RFPType.SPECIAL_NOTICE

    def test_type_a_maps_to_award(self):
        svc = make_service()
        raw = minimal_raw()
        raw["type"] = "a"
        opp = svc._parse_opportunity(raw)
        assert opp.rfp_type == RFPType.AWARD

    def test_unknown_type_defaults_to_solicitation(self):
        svc = make_service()
        raw = minimal_raw()
        raw["type"] = "z"
        opp = svc._parse_opportunity(raw)
        assert opp.rfp_type == RFPType.SOLICITATION

    def test_missing_type_defaults_to_solicitation(self):
        svc = make_service()
        raw = minimal_raw()
        del raw["type"]
        opp = svc._parse_opportunity(raw)
        assert opp.rfp_type == RFPType.SOLICITATION

    def test_uppercase_type_is_normalized(self):
        svc = make_service()
        raw = minimal_raw()
        raw["type"] = "O"
        opp = svc._parse_opportunity(raw)
        assert opp.rfp_type == RFPType.SOLICITATION


# =============================================================================
# parse_opportunity — public wrapper
# =============================================================================


class TestParseOpportunityPublicWrapper:
    def test_public_wrapper_returns_sam_opportunity(self):
        svc = make_service()
        opp = svc.parse_opportunity(minimal_raw())
        assert isinstance(opp, SAMOpportunity)

    def test_public_wrapper_delegates_to_private(self):
        svc = make_service()
        raw = minimal_raw()
        result_private = svc._parse_opportunity(raw)
        result_public = svc.parse_opportunity(raw)
        assert result_public.title == result_private.title
        assert result_public.rfp_type == result_private.rfp_type


# =============================================================================
# Mock mode — _mock_opportunities
# =============================================================================


class TestMockOpportunities:
    def test_mock_returns_sam_opportunities(self):
        svc = SAMGovService(mock_variant="v1")
        svc.mock = True
        params = SAMSearchParams(keywords="IT modernization", limit=3)
        opps = svc._mock_opportunities(params)
        assert len(opps) == 3
        for opp in opps:
            assert isinstance(opp, SAMOpportunity)

    def test_mock_respects_limit(self):
        svc = SAMGovService(mock_variant="v1")
        svc.mock = True
        params = SAMSearchParams(keywords="cloud", limit=1)
        opps = svc._mock_opportunities(params)
        assert len(opps) == 1

    def test_mock_v1_vs_v2_different_deadlines(self):
        svc_v1 = SAMGovService(mock_variant="v1")
        svc_v1.mock = True
        svc_v2 = SAMGovService(mock_variant="v2")
        svc_v2.mock = True
        params = SAMSearchParams(keywords="cloud", limit=1)
        opp_v1 = svc_v1._mock_opportunities(params)[0]
        opp_v2 = svc_v2._mock_opportunities(params)[0]
        # Different variants produce different deadline offsets
        assert opp_v1.response_deadline != opp_v2.response_deadline


# =============================================================================
# Circuit breaker
# =============================================================================


class TestCircuitBreaker:
    def test_circuit_closed_by_default(self):
        svc = SAMGovService.__new__(SAMGovService)
        svc.__class__._circuit_open_until = None
        with patch("app.services.ingest_service.settings") as mock_settings:
            mock_settings.sam_circuit_breaker_enabled = True
            assert svc._is_circuit_open() is False

    def test_circuit_closed_when_breaker_disabled(self):
        svc = SAMGovService.__new__(SAMGovService)
        with patch("app.services.ingest_service.settings") as mock_settings:
            mock_settings.sam_circuit_breaker_enabled = False
            svc.__class__._circuit_open_until = datetime.utcnow() + timedelta(seconds=300)
            assert svc._is_circuit_open() is False

    def test_sam_gov_api_error_attributes(self):
        err = SAMGovAPIError(
            "rate limited",
            status_code=429,
            retryable=False,
            is_rate_limited=True,
            retry_after_seconds=60,
        )
        assert err.status_code == 429
        assert err.is_rate_limited is True
        assert err.retryable is False
        assert err.retry_after_seconds == 60

    def test_sam_gov_api_error_message_in_str(self):
        err = SAMGovAPIError("API down", status_code=503)
        assert "API down" in str(err)
