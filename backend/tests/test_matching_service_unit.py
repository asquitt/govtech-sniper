"""
Matching Service Unit Tests
=============================
Tests for MatchResult, BatchMatchResult, and SCORING_CATEGORIES — no AI calls.
"""

from app.services.matching_service import (
    SCORING_CATEGORIES,
    BatchMatchResult,
    MatchResult,
)


class TestMatchResult:
    def test_to_dict(self):
        mr = MatchResult(
            overall_score=85.0,
            category_scores={"naics_fit": 90, "clearance_match": 80},
            strengths=["Strong NAICS match"],
            gaps=["Missing clearance"],
            reasoning="Good fit overall",
        )
        d = mr.to_dict()
        assert d["overall_score"] == 85.0
        assert d["category_scores"]["naics_fit"] == 90
        assert "Strong NAICS match" in d["strengths"]
        assert d["reasoning"] == "Good fit overall"

    def test_empty_result(self):
        mr = MatchResult(
            overall_score=0.0,
            category_scores={},
            strengths=[],
            gaps=[],
            reasoning="",
        )
        d = mr.to_dict()
        assert d["overall_score"] == 0.0
        assert d["strengths"] == []


class TestBatchMatchResult:
    def test_empty_batch(self):
        batch = BatchMatchResult()
        assert batch.results == []
        assert batch.errors == []

    def test_add_results(self):
        batch = BatchMatchResult()
        mr = MatchResult(50.0, {}, [], [], "")
        batch.results.append((1, mr))
        batch.errors.append((2, "API error"))
        assert len(batch.results) == 1
        assert len(batch.errors) == 1


class TestScoringCategories:
    def test_has_expected_categories(self):
        assert "naics_fit" in SCORING_CATEGORIES
        assert "clearance_match" in SCORING_CATEGORIES
        assert "past_performance_relevance" in SCORING_CATEGORIES

    def test_count(self):
        assert len(SCORING_CATEGORIES) == 8
