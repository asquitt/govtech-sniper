"""
Review Route Helper Unit Tests
================================
Tests for pure helper functions in reviews.py route module.
"""

from app.api.routes.reviews import (
    _review_packet_action_recommendation,
    _review_packet_exit_criteria,
)

# =============================================================================
# _review_packet_action_recommendation
# =============================================================================


class TestReviewPacketActionRecommendation:
    def test_closed_status(self):
        result = _review_packet_action_recommendation("critical", "closed")
        assert "No immediate action" in result

    def test_verified_status(self):
        result = _review_packet_action_recommendation("major", "verified")
        assert "No immediate action" in result

    def test_rejected_status(self):
        result = _review_packet_action_recommendation("minor", "rejected")
        assert "No immediate action" in result

    def test_critical_severity(self):
        result = _review_packet_action_recommendation("critical", "open")
        assert "immediate owner" in result.lower() or "patch" in result.lower()

    def test_major_severity(self):
        result = _review_packet_action_recommendation("major", "open")
        assert "draft cycle" in result.lower()

    def test_minor_severity(self):
        result = _review_packet_action_recommendation("minor", "open")
        assert "cleanup" in result.lower() or "quality" in result.lower()

    def test_suggestion_severity(self):
        result = _review_packet_action_recommendation("suggestion", "open")
        assert "discriminator" in result.lower() or "consider" in result.lower()


# =============================================================================
# _review_packet_exit_criteria
# =============================================================================


class TestReviewPacketExitCriteria:
    def test_pink_team(self):
        criteria = _review_packet_exit_criteria("pink", 80.0, 0, 2)
        assert len(criteria) == 3
        assert any("75%" in c for c in criteria)
        assert any("critical" in c.lower() for c in criteria)

    def test_red_team(self):
        criteria = _review_packet_exit_criteria("red", 90.0, 0, 1)
        assert len(criteria) == 3
        assert any("85%" in c for c in criteria)
        assert any("major" in c.lower() for c in criteria)

    def test_gold_team(self):
        criteria = _review_packet_exit_criteria("gold", 96.0, 0, 0)
        assert len(criteria) == 4
        assert any("95%" in c for c in criteria)
        assert any("go/no-go" in c.lower() for c in criteria)

    def test_unknown_type_defaults_to_gold(self):
        """Unknown review types fall through to the gold-level else branch."""
        criteria = _review_packet_exit_criteria("unknown", 50.0, 1, 3)
        assert len(criteria) == 4

    def test_criteria_contain_current_values(self):
        criteria = _review_packet_exit_criteria("pink", 72.5, 2, 5)
        joined = " ".join(criteria)
        assert "2" in joined  # open_critical count
        assert "72.5" in joined  # checklist pass rate
