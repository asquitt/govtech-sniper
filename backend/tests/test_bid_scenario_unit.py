"""
Bid Scenario Service Unit Tests
=================================
Tests for pure computation helpers — no DB, no AI.
"""

from app.models.capture import BidScorecardRecommendation
from app.services.bid_scenario_service import (
    BidScenarioService,
    ScenarioDefinition,
)


def _svc():
    return BidScenarioService()


# =============================================================================
# Static Helpers
# =============================================================================


class TestClamp:
    def test_within_range(self):
        assert BidScenarioService._clamp(50, 0, 100) == 50

    def test_below_lower(self):
        assert BidScenarioService._clamp(-5, 0, 100) == 0

    def test_above_upper(self):
        assert BidScenarioService._clamp(200, 0, 100) == 100

    def test_at_boundary(self):
        assert BidScenarioService._clamp(0, 0, 100) == 0
        assert BidScenarioService._clamp(100, 0, 100) == 100


class TestNormalizeCriterionName:
    def test_lowercase_strip(self):
        assert (
            BidScenarioService._normalize_criterion_name("  Technical_Capability  ")
            == "technical_capability"
        )


# =============================================================================
# Recommendation Thresholds
# =============================================================================


class TestRecommendationForScore:
    def test_bid(self):
        svc = _svc()
        assert svc._recommendation_for_score(70) == BidScorecardRecommendation.BID
        assert svc._recommendation_for_score(95) == BidScorecardRecommendation.BID

    def test_no_bid(self):
        svc = _svc()
        assert svc._recommendation_for_score(45) == BidScorecardRecommendation.NO_BID
        assert svc._recommendation_for_score(10) == BidScorecardRecommendation.NO_BID

    def test_conditional(self):
        svc = _svc()
        assert svc._recommendation_for_score(46) == BidScorecardRecommendation.CONDITIONAL
        assert svc._recommendation_for_score(69) == BidScorecardRecommendation.CONDITIONAL


# =============================================================================
# Weighted Score
# =============================================================================


class TestComputeWeightedScore:
    def test_simple(self):
        svc = _svc()
        criteria = [
            {"weight": 50, "score": 80},
            {"weight": 50, "score": 60},
        ]
        assert svc._compute_weighted_score(criteria) == 70.0

    def test_zero_weight(self):
        svc = _svc()
        assert svc._compute_weighted_score([]) == 0.0
        assert svc._compute_weighted_score([{"weight": 0, "score": 100}]) == 0.0


# =============================================================================
# Decision Risk Level
# =============================================================================


class TestDecisionRiskLevel:
    def test_high_score_high_confidence_low_risk(self):
        svc = _svc()
        level, risk = svc._decision_risk_level(90, 0.9)
        assert level in ("low", "medium")
        assert risk < 0.5

    def test_borderline_score_low_confidence_high_risk(self):
        svc = _svc()
        level, risk = svc._decision_risk_level(55, 0.1)
        assert level == "high"


# =============================================================================
# Default Scenarios
# =============================================================================


class TestDefaultScenarios:
    def test_returns_scenarios(self):
        svc = _svc()
        criteria = {
            "competitive_landscape",
            "price_competitiveness",
            "relationship_with_agency",
            "staffing_availability",
            "proposal_timeline",
            "technical_capability",
            "clearance_requirements",
            "set_aside_eligibility",
            "contract_vehicle_access",
            "teaming_strength",
            "past_performance",
        }
        scenarios = svc.default_scenarios(criteria)
        assert len(scenarios) == 4
        for s in scenarios:
            assert isinstance(s, ScenarioDefinition)
            assert len(s.adjustments) > 0

    def test_filters_missing_criteria(self):
        svc = _svc()
        # Only provide one criterion — some scenarios should be filtered out
        scenarios = svc.default_scenarios({"competitive_landscape"})
        for s in scenarios:
            for adj in s.adjustments:
                assert adj.criterion == "competitive_landscape"


# =============================================================================
# CRITERION_RATIONALE_MAP
# =============================================================================


class TestCriterionRationaleMap:
    def test_has_far_references(self):
        for key, val in BidScenarioService.CRITERION_RATIONALE_MAP.items():
            assert "far_reference" in val
            assert val["far_reference"].startswith("FAR")
            assert "section_m_factor" in val
