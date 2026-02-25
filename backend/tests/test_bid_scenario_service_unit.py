"""Unit tests for BidScenarioService."""

from unittest.mock import MagicMock

from app.models.capture import BidScorecardRecommendation
from app.services.bid_scenario_service import (
    BidScenarioService,
    ScenarioAdjustment,
    ScenarioDefinition,
)


def _make_scorecard(criteria_scores=None, overall_score=65.0, recommendation=None, confidence=0.7):
    sc = MagicMock()
    sc.id = 1
    sc.rfp_id = 10
    sc.criteria_scores = criteria_scores or []
    sc.overall_score = overall_score
    sc.recommendation = recommendation
    sc.confidence = confidence
    return sc


class TestClamp:
    def test_within_range(self):
        assert BidScenarioService._clamp(50, 0, 100) == 50

    def test_below_lower(self):
        assert BidScenarioService._clamp(-5, 0, 100) == 0

    def test_above_upper(self):
        assert BidScenarioService._clamp(150, 0, 100) == 100


class TestNormalizeCriterionName:
    def test_strips_and_lowercases(self):
        assert (
            BidScenarioService._normalize_criterion_name("  Technical_Capability  ")
            == "technical_capability"
        )


class TestRecommendationForScore:
    svc = BidScenarioService()

    def test_bid(self):
        assert self.svc._recommendation_for_score(80) == BidScorecardRecommendation.BID

    def test_no_bid(self):
        assert self.svc._recommendation_for_score(30) == BidScorecardRecommendation.NO_BID

    def test_conditional(self):
        assert self.svc._recommendation_for_score(55) == BidScorecardRecommendation.CONDITIONAL

    def test_boundary_70(self):
        assert self.svc._recommendation_for_score(70) == BidScorecardRecommendation.BID

    def test_boundary_45(self):
        assert self.svc._recommendation_for_score(45) == BidScorecardRecommendation.NO_BID


class TestComputeWeightedScore:
    svc = BidScenarioService()

    def test_basic_calculation(self):
        criteria = [
            {"weight": 30, "score": 80},
            {"weight": 70, "score": 60},
        ]
        result = self.svc._compute_weighted_score(criteria)
        expected = (30 * 80 + 70 * 60) / 100
        assert abs(result - expected) < 0.01

    def test_empty_criteria(self):
        assert self.svc._compute_weighted_score([]) == 0.0

    def test_zero_weight(self):
        criteria = [{"weight": 0, "score": 50}]
        assert self.svc._compute_weighted_score(criteria) == 0.0


class TestBaselineCriteria:
    svc = BidScenarioService()

    def test_uses_scorecard_criteria(self):
        scorecard = _make_scorecard(
            criteria_scores=[
                {"name": "Technical_Capability", "weight": 40, "score": 75, "reasoning": "Strong"},
                {"name": "Past_Performance", "weight": 60, "score": 85, "reasoning": "Excellent"},
            ]
        )
        result = self.svc._baseline_criteria(scorecard)
        assert len(result) == 2
        assert result[0]["name"] == "technical_capability"
        assert result[0]["score"] == 75.0

    def test_fallback_when_no_criteria(self):
        scorecard = _make_scorecard(criteria_scores=[], overall_score=60.0)
        result = self.svc._baseline_criteria(scorecard)
        assert len(result) > 0
        assert all(item["score"] == 60.0 for item in result)

    def test_skips_empty_names(self):
        scorecard = _make_scorecard(
            criteria_scores=[
                {"name": "", "weight": 50, "score": 70},
                {"name": "valid", "weight": 50, "score": 80},
            ]
        )
        result = self.svc._baseline_criteria(scorecard)
        assert len(result) == 1
        assert result[0]["name"] == "valid"


class TestDefaultScenarios:
    svc = BidScenarioService()

    def test_returns_scenarios_for_known_criteria(self):
        criteria = {
            "competitive_landscape",
            "price_competitiveness",
            "relationship_with_agency",
            "staffing_availability",
            "proposal_timeline",
            "technical_capability",
        }
        scenarios = self.svc.default_scenarios(criteria)
        assert len(scenarios) >= 2
        assert all(isinstance(s, ScenarioDefinition) for s in scenarios)

    def test_filters_unavailable_criteria(self):
        scenarios = self.svc.default_scenarios({"competitive_landscape"})
        for s in scenarios:
            for adj in s.adjustments:
                assert self.svc._normalize_criterion_name(adj.criterion) == "competitive_landscape"

    def test_empty_criteria_returns_empty(self):
        scenarios = self.svc.default_scenarios(set())
        assert scenarios == []


class TestSimulate:
    svc = BidScenarioService()

    def test_basic_simulation(self):
        scorecard = _make_scorecard(
            criteria_scores=[
                {"name": "technical_capability", "weight": 50, "score": 80},
                {"name": "past_performance", "weight": 50, "score": 70},
            ],
            recommendation=BidScorecardRecommendation.BID,
            confidence=0.75,
        )
        scenarios = [
            ScenarioDefinition(
                name="Test Scenario",
                adjustments=[ScenarioAdjustment("technical_capability", -20.0, "Degraded")],
            )
        ]
        result = self.svc.simulate(scorecard, scenarios)

        assert result["rfp_id"] == 10
        assert result["baseline"]["overall_score"] == 75.0
        assert len(result["scenarios"]) == 1
        scenario = result["scenarios"][0]
        assert scenario["name"] == "Test Scenario"
        assert scenario["overall_score"] < 75.0

    def test_scenario_with_no_adjustments(self):
        scorecard = _make_scorecard(
            criteria_scores=[
                {"name": "technical_capability", "weight": 100, "score": 60},
            ],
            recommendation=BidScorecardRecommendation.CONDITIONAL,
        )
        scenarios = [ScenarioDefinition(name="No Change", adjustments=[])]
        result = self.svc.simulate(scorecard, scenarios)
        assert result["scenarios"][0]["overall_score"] == 60.0

    def test_ignored_adjustments_tracked(self):
        scorecard = _make_scorecard(
            criteria_scores=[
                {"name": "technical_capability", "weight": 100, "score": 70},
            ],
            recommendation=BidScorecardRecommendation.BID,
        )
        scenarios = [
            ScenarioDefinition(
                name="Unknown Criterion",
                adjustments=[ScenarioAdjustment("nonexistent_criterion", -10.0, "Unknown")],
            )
        ]
        result = self.svc.simulate(scorecard, scenarios)
        assert len(result["scenarios"][0]["ignored_adjustments"]) == 1

    def test_score_clamped_to_bounds(self):
        scorecard = _make_scorecard(
            criteria_scores=[
                {"name": "technical_capability", "weight": 100, "score": 95},
            ],
            recommendation=BidScorecardRecommendation.BID,
        )
        scenarios = [
            ScenarioDefinition(
                name="Over 100",
                adjustments=[ScenarioAdjustment("technical_capability", 50.0, "Boost")],
            )
        ]
        result = self.svc.simulate(scorecard, scenarios)
        assert result["scenarios"][0]["overall_score"] == 100.0

    def test_decision_risk_present(self):
        scorecard = _make_scorecard(
            criteria_scores=[
                {"name": "technical_capability", "weight": 100, "score": 70},
            ],
            recommendation=BidScorecardRecommendation.BID,
        )
        scenarios = [
            ScenarioDefinition(
                name="Risk Check",
                adjustments=[ScenarioAdjustment("technical_capability", -30.0)],
            )
        ]
        result = self.svc.simulate(scorecard, scenarios)
        scenario = result["scenarios"][0]
        assert scenario["decision_risk"] in ("low", "medium", "high")
        assert 0 <= scenario["risk_score"] <= 1
