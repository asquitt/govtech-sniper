"""
Killer Filter Unit Tests
=========================
Tests for quick_disqualify() and FilterResult — pure logic, no AI.
"""

from unittest.mock import MagicMock

from app.models.user import ClearanceLevel
from app.services.filters import FilterResult, quick_disqualify


def _mock_rfp(**kwargs):
    rfp = MagicMock()
    rfp.naics_code = kwargs.get("naics_code")
    rfp.set_aside = kwargs.get("set_aside")
    rfp.estimated_value = kwargs.get("estimated_value")
    rfp.title = kwargs.get("title", "Test RFP")
    rfp.description = kwargs.get("description")
    return rfp


def _mock_profile(**kwargs):
    profile = MagicMock()
    profile.naics_codes = kwargs.get("naics_codes", [])
    profile.set_aside_types = kwargs.get("set_aside_types", [])
    profile.min_contract_value = kwargs.get("min_contract_value")
    profile.max_contract_value = kwargs.get("max_contract_value")
    profile.exclude_keywords = kwargs.get("exclude_keywords", [])
    profile.clearance_level = kwargs.get("clearance_level", ClearanceLevel.NONE)
    profile.preferred_states = kwargs.get("preferred_states", [])
    profile.include_keywords = kwargs.get("include_keywords", [])
    return profile


class TestQuickDisqualifyNAICS:
    def test_matching_naics_passes(self):
        rfp = _mock_rfp(naics_code="541512")
        profile = _mock_profile(naics_codes=["541512", "541511"])
        assert quick_disqualify(rfp, profile) is None

    def test_same_industry_group_passes(self):
        """First 4 digits match → proceed to AI filter."""
        rfp = _mock_rfp(naics_code="541519")
        profile = _mock_profile(naics_codes=["541512"])
        assert quick_disqualify(rfp, profile) is None

    def test_different_industry_group_disqualifies(self):
        rfp = _mock_rfp(naics_code="236220")
        profile = _mock_profile(naics_codes=["541512"])
        result = quick_disqualify(rfp, profile)
        assert result is not None
        assert "NAICS" in result

    def test_no_naics_on_rfp_passes(self):
        rfp = _mock_rfp(naics_code=None)
        profile = _mock_profile(naics_codes=["541512"])
        assert quick_disqualify(rfp, profile) is None

    def test_no_naics_on_profile_passes(self):
        rfp = _mock_rfp(naics_code="541512")
        profile = _mock_profile(naics_codes=[])
        assert quick_disqualify(rfp, profile) is None


class TestQuickDisqualifySetAside:
    def test_full_and_open_always_passes(self):
        rfp = _mock_rfp(set_aside="Full and Open")
        profile = _mock_profile(set_aside_types=[])
        assert quick_disqualify(rfp, profile) is None

    def test_matching_set_aside_passes(self):
        rfp = _mock_rfp(set_aside="8(a)")
        profile = _mock_profile(set_aside_types=["8(a)"])
        assert quick_disqualify(rfp, profile) is None

    def test_mismatched_set_aside_disqualifies(self):
        rfp = _mock_rfp(set_aside="HUBZone")
        profile = _mock_profile(set_aside_types=["8(a)", "WOSB"])
        result = quick_disqualify(rfp, profile)
        assert result is not None
        assert "Set-aside" in result

    def test_sdvosb_matching(self):
        rfp = _mock_rfp(set_aside="Service-Disabled Veteran")
        profile = _mock_profile(set_aside_types=["SDVOSB"])
        assert quick_disqualify(rfp, profile) is None

    def test_no_set_aside_passes(self):
        rfp = _mock_rfp(set_aside=None)
        profile = _mock_profile(set_aside_types=[])
        assert quick_disqualify(rfp, profile) is None


class TestQuickDisqualifyContractValue:
    def test_within_range_passes(self):
        rfp = _mock_rfp(estimated_value=500000)
        profile = _mock_profile(min_contract_value=100000, max_contract_value=1000000)
        assert quick_disqualify(rfp, profile) is None

    def test_below_minimum_disqualifies(self):
        rfp = _mock_rfp(estimated_value=50000)
        profile = _mock_profile(min_contract_value=100000)
        result = quick_disqualify(rfp, profile)
        assert result is not None
        assert "below minimum" in result

    def test_above_maximum_disqualifies(self):
        rfp = _mock_rfp(estimated_value=5000000)
        profile = _mock_profile(max_contract_value=1000000)
        result = quick_disqualify(rfp, profile)
        assert result is not None
        assert "exceeds maximum" in result

    def test_no_value_passes(self):
        rfp = _mock_rfp(estimated_value=None)
        profile = _mock_profile(min_contract_value=100000)
        assert quick_disqualify(rfp, profile) is None


class TestQuickDisqualifyExcludedKeywords:
    def test_excluded_keyword_in_title_disqualifies(self):
        rfp = _mock_rfp(title="Construction of Building", description="")
        profile = _mock_profile(exclude_keywords=["construction"])
        result = quick_disqualify(rfp, profile)
        assert result is not None
        assert "excluded keyword" in result

    def test_excluded_keyword_in_description_disqualifies(self):
        rfp = _mock_rfp(title="IT Services", description="Requires janitorial support")
        profile = _mock_profile(exclude_keywords=["janitorial"])
        result = quick_disqualify(rfp, profile)
        assert result is not None

    def test_no_excluded_keywords_passes(self):
        rfp = _mock_rfp(title="Cybersecurity RFP", description="Advanced threat detection")
        profile = _mock_profile(exclude_keywords=["construction", "janitorial"])
        assert quick_disqualify(rfp, profile) is None


class TestFilterResult:
    def test_to_dict(self):
        fr = FilterResult(
            is_qualified=True,
            reason="Good match",
            confidence=0.85,
            disqualifying_factors=[],
            matching_factors=["NAICS match"],
        )
        d = fr.to_dict()
        assert d["is_qualified"] is True
        assert d["confidence"] == 0.85
        assert d["matching_factors"] == ["NAICS match"]
