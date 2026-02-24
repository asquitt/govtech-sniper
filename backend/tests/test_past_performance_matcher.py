"""
Past Performance Matcher Unit Tests
=====================================
Tests for PastPerformanceMatch data class.
The async DB functions (match_past_performances, generate_narrative) are not
tested here since they require a live session.
"""

from app.services.past_performance_matcher import PastPerformanceMatch

# =============================================================================
# PastPerformanceMatch
# =============================================================================


class TestPastPerformanceMatch:
    def test_init_stores_fields(self):
        match = PastPerformanceMatch(
            document_id=42,
            title="IT Modernization",
            score=75.5,
            matching_criteria=["NAICS code match: 541512"],
        )
        assert match.document_id == 42
        assert match.title == "IT Modernization"
        assert match.score == 75.5
        assert match.matching_criteria == ["NAICS code match: 541512"]

    def test_empty_criteria_list(self):
        match = PastPerformanceMatch(
            document_id=1,
            title="Test",
            score=0.0,
            matching_criteria=[],
        )
        assert match.matching_criteria == []

    def test_multiple_criteria(self):
        criteria = [
            "NAICS code match: 541512",
            "Agency match: Department of Defense",
            "Recent performance (within 3 years)",
        ]
        match = PastPerformanceMatch(
            document_id=10,
            title="Cloud Migration",
            score=85.0,
            matching_criteria=criteria,
        )
        assert len(match.matching_criteria) == 3
        assert "Agency match: Department of Defense" in match.matching_criteria

    def test_score_can_be_zero(self):
        match = PastPerformanceMatch(document_id=1, title="Test", score=0.0, matching_criteria=[])
        assert match.score == 0.0

    def test_score_can_be_max(self):
        match = PastPerformanceMatch(
            document_id=1, title="Test", score=100.0, matching_criteria=["Full match"]
        )
        assert match.score == 100.0
