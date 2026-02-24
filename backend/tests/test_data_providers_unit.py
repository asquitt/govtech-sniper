"""Unit tests for data_providers base classes and registry."""

from app.services.data_providers import get_provider, list_providers
from app.services.data_providers.base import (
    DataSourceProvider,
    ProviderMaturity,
    RawOpportunity,
    SearchParams,
)


# ---------------------------------------------------------------------------
# SearchParams
# ---------------------------------------------------------------------------
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
            agency="DOD",
            days_back=30,
            limit=50,
        )
        assert params.keywords == "cybersecurity"
        assert params.naics_codes == ["541512"]
        assert params.limit == 50

    def test_serialization(self):
        params = SearchParams(keywords="test")
        data = params.model_dump()
        assert data["keywords"] == "test"
        assert data["days_back"] == 90


# ---------------------------------------------------------------------------
# RawOpportunity
# ---------------------------------------------------------------------------
class TestRawOpportunity:
    def test_required_fields(self):
        opp = RawOpportunity(
            external_id="EXT-001",
            title="Test Opp",
            source_type="gsa_ebuy",
        )
        assert opp.external_id == "EXT-001"
        assert opp.title == "Test Opp"
        assert opp.source_type == "gsa_ebuy"

    def test_optional_fields_default_none(self):
        opp = RawOpportunity(
            external_id="EXT-002",
            title="Minimal",
            source_type="test",
        )
        assert opp.agency is None
        assert opp.description is None
        assert opp.posted_date is None
        assert opp.response_deadline is None
        assert opp.estimated_value is None
        assert opp.currency is None
        assert opp.jurisdiction is None
        assert opp.naics_code is None
        assert opp.source_url is None
        assert opp.raw_data is None

    def test_all_fields(self):
        opp = RawOpportunity(
            external_id="EXT-003",
            title="Full Opp",
            agency="DoD",
            description="Cybersecurity services",
            posted_date="2025-01-01",
            response_deadline="2025-03-01",
            estimated_value=1000000.0,
            currency="USD",
            jurisdiction="federal",
            naics_code="541512",
            source_url="https://sam.gov/opp/123",
            source_type="sam_gov",
            raw_data={"key": "value"},
        )
        assert opp.estimated_value == 1000000.0
        assert opp.raw_data == {"key": "value"}

    def test_serialization(self):
        opp = RawOpportunity(
            external_id="EXT-004",
            title="Serialize Test",
            source_type="test",
        )
        data = opp.model_dump()
        assert data["external_id"] == "EXT-004"


# ---------------------------------------------------------------------------
# ProviderMaturity enum
# ---------------------------------------------------------------------------
class TestProviderMaturity:
    def test_values(self):
        assert ProviderMaturity.LIVE == "LIVE"
        assert ProviderMaturity.HYBRID == "HYBRID"
        assert ProviderMaturity.SAMPLE == "SAMPLE"


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------
class TestProviderRegistry:
    def test_get_known_provider(self):
        provider = get_provider("gsa_ebuy")
        assert provider is not None
        assert provider.provider_name == "gsa_ebuy"

    def test_get_unknown_provider_returns_none(self):
        assert get_provider("nonexistent") is None

    def test_list_providers_returns_all(self):
        providers = list_providers()
        assert len(providers) > 0
        names = {p.provider_name for p in providers}
        assert "gsa_ebuy" in names
        assert "fpds" in names
        assert "usaspending" in names

    def test_all_providers_have_required_attributes(self):
        for provider in list_providers():
            assert hasattr(provider, "provider_name")
            assert hasattr(provider, "display_name")
            assert hasattr(provider, "description")
            assert hasattr(provider, "is_active")
            assert hasattr(provider, "maturity")

    def test_known_providers_registered(self):
        expected = [
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
            "grants_gov",
            "canada_buyandsell",
            "canada_provincial",
        ]
        for name in expected:
            assert get_provider(name) is not None, f"Provider {name} not found"

    def test_providers_are_data_source_provider_instances(self):
        for provider in list_providers():
            assert isinstance(provider, DataSourceProvider)

    def test_each_provider_has_unique_name(self):
        providers = list_providers()
        names = [p.provider_name for p in providers]
        assert len(names) == len(set(names))
