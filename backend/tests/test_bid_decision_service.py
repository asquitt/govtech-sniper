"""
Bid Decision Service Unit Tests
================================
Tests for pure-logic functions in bid_decision_service.
(AI evaluation tested separately via mocks.)
"""

from app.services.bid_decision_service import (
    DEFAULT_BID_CRITERIA,
    BidDecisionService,
)


class TestDefaultCriteria:
    def test_weights_sum_to_100(self):
        total = sum(c["weight"] for c in DEFAULT_BID_CRITERIA)
        assert total == 100

    def test_all_criteria_have_required_fields(self):
        for c in DEFAULT_BID_CRITERIA:
            assert "name" in c
            assert "weight" in c
            assert "description" in c
            assert isinstance(c["weight"], int)
            assert c["weight"] > 0


class TestComputeWinProbability:
    def test_perfect_scores(self):
        """All 100 scores → 100% win probability."""

        class MockScorecard:
            criteria_scores = [
                {"name": "tech", "weight": 50, "score": 100},
                {"name": "price", "weight": 50, "score": 100},
            ]

        prob = BidDecisionService.compute_win_probability(MockScorecard())
        assert prob == 100

    def test_zero_scores(self):
        class MockScorecard:
            criteria_scores = [
                {"name": "tech", "weight": 50, "score": 0},
                {"name": "price", "weight": 50, "score": 0},
            ]

        prob = BidDecisionService.compute_win_probability(MockScorecard())
        assert prob == 0

    def test_weighted_average(self):
        class MockScorecard:
            criteria_scores = [
                {"name": "tech", "weight": 80, "score": 100},
                {"name": "price", "weight": 20, "score": 0},
            ]

        prob = BidDecisionService.compute_win_probability(MockScorecard())
        assert prob == 80

    def test_empty_scores(self):
        class MockScorecard:
            criteria_scores = []

        prob = BidDecisionService.compute_win_probability(MockScorecard())
        assert prob == 0

    def test_missing_weight_defaults_to_1(self):
        class MockScorecard:
            criteria_scores = [
                {"name": "tech", "score": 60},
                {"name": "price", "score": 80},
            ]

        prob = BidDecisionService.compute_win_probability(MockScorecard())
        assert prob == 70  # (60 + 80) / 2
