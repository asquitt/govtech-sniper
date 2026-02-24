"""
RFP Downloader Unit Tests
===========================
Tests for WinProbabilityScorer.calculate_score and DownloadedDocument.
Network/file I/O methods (RFPDownloader) are not tested here.
"""

from datetime import datetime, timedelta

import pytest

from app.services.rfp_downloader import DownloadedDocument, WinProbabilityScorer

# =============================================================================
# DownloadedDocument
# =============================================================================


class TestDownloadedDocument:
    def test_required_fields(self):
        doc = DownloadedDocument(
            filename="rfp.pdf",
            file_path="/tmp/rfps/1/rfp.pdf",
            file_size=1024,
            mime_type="application/pdf",
            content_hash="abc123",
        )
        assert doc.filename == "rfp.pdf"
        assert doc.file_path == "/tmp/rfps/1/rfp.pdf"
        assert doc.file_size == 1024
        assert doc.mime_type == "application/pdf"
        assert doc.content_hash == "abc123"

    def test_optional_fields_default_none(self):
        doc = DownloadedDocument(
            filename="rfp.pdf",
            file_path="/tmp/rfps/1/rfp.pdf",
            file_size=1024,
            mime_type="application/pdf",
            content_hash="abc123",
        )
        assert doc.extracted_text is None
        assert doc.page_count is None

    def test_optional_fields_set(self):
        doc = DownloadedDocument(
            filename="rfp.pdf",
            file_path="/tmp/rfps/1/rfp.pdf",
            file_size=2048,
            mime_type="application/pdf",
            content_hash="def456",
            extracted_text="Some extracted text",
            page_count=10,
        )
        assert doc.extracted_text == "Some extracted text"
        assert doc.page_count == 10


# =============================================================================
# WinProbabilityScorer.calculate_score
# =============================================================================


@pytest.fixture
def scorer():
    return WinProbabilityScorer()


def _base_rfp(**overrides) -> dict:
    """Minimal RFP data with sensible defaults."""
    base = {
        "naics_code": "541512",
        "set_aside": "Full and Open",
        "required_clearance": "none",
        "place_of_performance": "Washington, DC",
        "estimated_value": 500_000,
        "response_deadline": (datetime.utcnow() + timedelta(days=30)).isoformat(),
    }
    base.update(overrides)
    return base


def _base_profile(**overrides) -> dict:
    """Minimal user profile with sensible defaults."""
    base = {
        "naics_codes": ["541512"],
        "set_aside_types": ["Small Business"],
        "clearance_level": "secret",
        "preferred_states": ["DC"],
        "min_contract_value": 100_000,
        "max_contract_value": 1_000_000,
    }
    base.update(overrides)
    return base


class TestWinProbabilityScorerNAICS:
    @pytest.mark.asyncio
    async def test_exact_naics_match_scores_100(self, scorer: WinProbabilityScorer):
        result = await scorer.calculate_score(
            _base_rfp(naics_code="541512"),
            _base_profile(naics_codes=["541512"]),
        )
        assert result["breakdown"]["naics_match"] == 100

    @pytest.mark.asyncio
    async def test_four_digit_naics_match_scores_70(self, scorer: WinProbabilityScorer):
        result = await scorer.calculate_score(
            _base_rfp(naics_code="541519"),
            _base_profile(naics_codes=["541512"]),
        )
        assert result["breakdown"]["naics_match"] == 70

    @pytest.mark.asyncio
    async def test_two_digit_naics_match_scores_40(self, scorer: WinProbabilityScorer):
        result = await scorer.calculate_score(
            _base_rfp(naics_code="549999"),
            _base_profile(naics_codes=["541512"]),
        )
        assert result["breakdown"]["naics_match"] == 40

    @pytest.mark.asyncio
    async def test_no_naics_match_scores_20(self, scorer: WinProbabilityScorer):
        result = await scorer.calculate_score(
            _base_rfp(naics_code="111111"),
            _base_profile(naics_codes=["541512"]),
        )
        assert result["breakdown"]["naics_match"] == 20

    @pytest.mark.asyncio
    async def test_empty_rfp_naics_scores_20(self, scorer: WinProbabilityScorer):
        result = await scorer.calculate_score(
            _base_rfp(naics_code=""),
            _base_profile(naics_codes=["541512"]),
        )
        assert result["breakdown"]["naics_match"] == 20


class TestWinProbabilityScorerSetAside:
    @pytest.mark.asyncio
    async def test_full_and_open_scores_100(self, scorer: WinProbabilityScorer):
        result = await scorer.calculate_score(
            _base_rfp(set_aside="Full and Open"),
            _base_profile(),
        )
        assert result["breakdown"]["set_aside_match"] == 100

    @pytest.mark.asyncio
    async def test_none_set_aside_scores_100(self, scorer: WinProbabilityScorer):
        result = await scorer.calculate_score(
            _base_rfp(set_aside="None"),
            _base_profile(),
        )
        assert result["breakdown"]["set_aside_match"] == 100

    @pytest.mark.asyncio
    async def test_empty_set_aside_scores_100(self, scorer: WinProbabilityScorer):
        result = await scorer.calculate_score(
            _base_rfp(set_aside=""),
            _base_profile(),
        )
        assert result["breakdown"]["set_aside_match"] == 100

    @pytest.mark.asyncio
    async def test_matching_set_aside_scores_100(self, scorer: WinProbabilityScorer):
        result = await scorer.calculate_score(
            _base_rfp(set_aside="Small Business Set-Aside"),
            _base_profile(set_aside_types=["Small Business"]),
        )
        assert result["breakdown"]["set_aside_match"] == 100

    @pytest.mark.asyncio
    async def test_non_matching_set_aside_scores_0(self, scorer: WinProbabilityScorer):
        result = await scorer.calculate_score(
            _base_rfp(set_aside="8(a) Set-Aside"),
            _base_profile(set_aside_types=["HUBZone"]),
        )
        assert result["breakdown"]["set_aside_match"] == 0


class TestWinProbabilityScorerClearance:
    @pytest.mark.asyncio
    async def test_user_meets_clearance_scores_100(self, scorer: WinProbabilityScorer):
        result = await scorer.calculate_score(
            _base_rfp(required_clearance="secret"),
            _base_profile(clearance_level="top_secret"),
        )
        assert result["breakdown"]["clearance_match"] == 100

    @pytest.mark.asyncio
    async def test_exact_clearance_match_scores_100(self, scorer: WinProbabilityScorer):
        result = await scorer.calculate_score(
            _base_rfp(required_clearance="secret"),
            _base_profile(clearance_level="secret"),
        )
        assert result["breakdown"]["clearance_match"] == 100

    @pytest.mark.asyncio
    async def test_insufficient_clearance_scores_0(self, scorer: WinProbabilityScorer):
        result = await scorer.calculate_score(
            _base_rfp(required_clearance="top_secret"),
            _base_profile(clearance_level="secret"),
        )
        assert result["breakdown"]["clearance_match"] == 0

    @pytest.mark.asyncio
    async def test_no_clearance_required_scores_100(self, scorer: WinProbabilityScorer):
        result = await scorer.calculate_score(
            _base_rfp(required_clearance="none"),
            _base_profile(clearance_level="none"),
        )
        assert result["breakdown"]["clearance_match"] == 100


class TestWinProbabilityScorerGeographic:
    @pytest.mark.asyncio
    async def test_matching_state_scores_100(self, scorer: WinProbabilityScorer):
        result = await scorer.calculate_score(
            _base_rfp(place_of_performance="Washington, DC"),
            _base_profile(preferred_states=["DC"]),
        )
        assert result["breakdown"]["geographic_match"] == 100

    @pytest.mark.asyncio
    async def test_no_preference_scores_80(self, scorer: WinProbabilityScorer):
        result = await scorer.calculate_score(
            _base_rfp(place_of_performance=""),
            _base_profile(preferred_states=[]),
        )
        assert result["breakdown"]["geographic_match"] == 80

    @pytest.mark.asyncio
    async def test_different_location_scores_50(self, scorer: WinProbabilityScorer):
        result = await scorer.calculate_score(
            _base_rfp(place_of_performance="San Diego, CA"),
            _base_profile(preferred_states=["DC", "VA"]),
        )
        assert result["breakdown"]["geographic_match"] == 50


class TestWinProbabilityScorerContractValue:
    @pytest.mark.asyncio
    async def test_within_range_scores_100(self, scorer: WinProbabilityScorer):
        result = await scorer.calculate_score(
            _base_rfp(estimated_value=500_000),
            _base_profile(min_contract_value=100_000, max_contract_value=1_000_000),
        )
        assert result["breakdown"]["contract_value_fit"] == 100

    @pytest.mark.asyncio
    async def test_unknown_value_scores_70(self, scorer: WinProbabilityScorer):
        result = await scorer.calculate_score(
            _base_rfp(estimated_value=0),
            _base_profile(),
        )
        assert result["breakdown"]["contract_value_fit"] == 70

    @pytest.mark.asyncio
    async def test_too_small_scores_40(self, scorer: WinProbabilityScorer):
        result = await scorer.calculate_score(
            _base_rfp(estimated_value=10_000),
            _base_profile(min_contract_value=100_000, max_contract_value=1_000_000),
        )
        assert result["breakdown"]["contract_value_fit"] == 40

    @pytest.mark.asyncio
    async def test_too_large_scores_60(self, scorer: WinProbabilityScorer):
        result = await scorer.calculate_score(
            _base_rfp(estimated_value=5_000_000),
            _base_profile(min_contract_value=100_000, max_contract_value=1_000_000),
        )
        assert result["breakdown"]["contract_value_fit"] == 60


class TestWinProbabilityScorerPastPerformance:
    @pytest.mark.asyncio
    async def test_no_past_performance_scores_30(self, scorer: WinProbabilityScorer):
        result = await scorer.calculate_score(
            _base_rfp(),
            _base_profile(),
            past_performance=None,
        )
        assert result["breakdown"]["past_performance"] == 30

    @pytest.mark.asyncio
    async def test_with_past_performance_averages(self, scorer: WinProbabilityScorer):
        pp = [
            {"relevance_score": 80},
            {"relevance_score": 60},
        ]
        result = await scorer.calculate_score(
            _base_rfp(),
            _base_profile(),
            past_performance=pp,
        )
        assert result["breakdown"]["past_performance"] == 70.0

    @pytest.mark.asyncio
    async def test_limits_to_top_5(self, scorer: WinProbabilityScorer):
        pp = [{"relevance_score": 100} for _ in range(10)]
        result = await scorer.calculate_score(
            _base_rfp(),
            _base_profile(),
            past_performance=pp,
        )
        assert result["breakdown"]["past_performance"] == 100.0


class TestWinProbabilityScorerDeadline:
    @pytest.mark.asyncio
    async def test_past_due_scores_0(self, scorer: WinProbabilityScorer):
        result = await scorer.calculate_score(
            _base_rfp(response_deadline=(datetime.utcnow() - timedelta(days=5)).isoformat()),
            _base_profile(),
        )
        assert result["breakdown"]["deadline_feasibility"] == 0

    @pytest.mark.asyncio
    async def test_very_tight_scores_40(self, scorer: WinProbabilityScorer):
        result = await scorer.calculate_score(
            _base_rfp(response_deadline=(datetime.utcnow() + timedelta(days=3)).isoformat()),
            _base_profile(),
        )
        assert result["breakdown"]["deadline_feasibility"] == 40

    @pytest.mark.asyncio
    async def test_tight_scores_70(self, scorer: WinProbabilityScorer):
        result = await scorer.calculate_score(
            _base_rfp(response_deadline=(datetime.utcnow() + timedelta(days=10)).isoformat()),
            _base_profile(),
        )
        assert result["breakdown"]["deadline_feasibility"] == 70

    @pytest.mark.asyncio
    async def test_comfortable_scores_90(self, scorer: WinProbabilityScorer):
        result = await scorer.calculate_score(
            _base_rfp(response_deadline=(datetime.utcnow() + timedelta(days=20)).isoformat()),
            _base_profile(),
        )
        assert result["breakdown"]["deadline_feasibility"] == 90

    @pytest.mark.asyncio
    async def test_plenty_of_time_scores_100(self, scorer: WinProbabilityScorer):
        result = await scorer.calculate_score(
            _base_rfp(response_deadline=(datetime.utcnow() + timedelta(days=45)).isoformat()),
            _base_profile(),
        )
        assert result["breakdown"]["deadline_feasibility"] == 100

    @pytest.mark.asyncio
    async def test_no_deadline_scores_70(self, scorer: WinProbabilityScorer):
        result = await scorer.calculate_score(
            _base_rfp(response_deadline=None),
            _base_profile(),
        )
        assert result["breakdown"]["deadline_feasibility"] == 70


class TestWinProbabilityScorerOverall:
    @pytest.mark.asyncio
    async def test_returns_required_keys(self, scorer: WinProbabilityScorer):
        result = await scorer.calculate_score(_base_rfp(), _base_profile())
        assert "total_score" in result
        assert "rating" in result
        assert "recommendation" in result
        assert "breakdown" in result
        assert "weights" in result

    @pytest.mark.asyncio
    async def test_total_score_is_rounded(self, scorer: WinProbabilityScorer):
        result = await scorer.calculate_score(_base_rfp(), _base_profile())
        assert result["total_score"] == round(result["total_score"], 1)

    @pytest.mark.asyncio
    async def test_high_rating_above_80(self, scorer: WinProbabilityScorer):
        # All perfect scores
        result = await scorer.calculate_score(
            _base_rfp(
                naics_code="541512",
                set_aside="Full and Open",
                required_clearance="none",
                place_of_performance="DC",
                estimated_value=500_000,
                response_deadline=(datetime.utcnow() + timedelta(days=60)).isoformat(),
            ),
            _base_profile(),
            past_performance=[{"relevance_score": 100}],
        )
        assert result["total_score"] >= 80
        assert result["rating"] == "High"

    @pytest.mark.asyncio
    async def test_very_low_rating_below_40(self, scorer: WinProbabilityScorer):
        result = await scorer.calculate_score(
            _base_rfp(
                naics_code="111111",
                set_aside="8(a) Set-Aside",
                required_clearance="ts_sci",
                place_of_performance="Guam",
                estimated_value=50_000_000,
                response_deadline=(datetime.utcnow() - timedelta(days=10)).isoformat(),
            ),
            _base_profile(
                naics_codes=["541512"],
                set_aside_types=["HUBZone"],
                clearance_level="none",
                preferred_states=["DC"],
                min_contract_value=100_000,
                max_contract_value=1_000_000,
            ),
            past_performance=None,
        )
        assert result["total_score"] < 40
        assert result["rating"] == "Very Low"

    @pytest.mark.asyncio
    async def test_weights_sum_to_one(self, scorer: WinProbabilityScorer):
        result = await scorer.calculate_score(_base_rfp(), _base_profile())
        assert abs(sum(result["weights"].values()) - 1.0) < 0.001
