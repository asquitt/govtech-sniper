"""
Review Checklist Templates Unit Tests
=======================================
Tests for checklist template data structures and lookup function.
"""

from app.services.review_checklist_templates import (
    GOLD_TEAM_CHECKLIST,
    PINK_TEAM_CHECKLIST,
    RED_TEAM_CHECKLIST,
    get_checklist_template,
)

# =============================================================================
# get_checklist_template
# =============================================================================


class TestGetChecklistTemplate:
    def test_pink_returns_pink_checklist(self):
        result = get_checklist_template("pink")
        assert result is PINK_TEAM_CHECKLIST

    def test_red_returns_red_checklist(self):
        result = get_checklist_template("red")
        assert result is RED_TEAM_CHECKLIST

    def test_gold_returns_gold_checklist(self):
        result = get_checklist_template("gold")
        assert result is GOLD_TEAM_CHECKLIST

    def test_unknown_type_returns_empty_list(self):
        assert get_checklist_template("blue") == []

    def test_empty_string_returns_empty_list(self):
        assert get_checklist_template("") == []

    def test_case_sensitive_uppercase_returns_empty(self):
        assert get_checklist_template("Pink") == []

    def test_case_sensitive_mixed_returns_empty(self):
        assert get_checklist_template("RED") == []


# =============================================================================
# Checklist Structure Validation
# =============================================================================


class TestPinkTeamChecklist:
    def test_has_items(self):
        assert len(PINK_TEAM_CHECKLIST) > 0

    def test_all_items_have_required_keys(self):
        for item in PINK_TEAM_CHECKLIST:
            assert "category" in item
            assert "item_text" in item
            assert "display_order" in item

    def test_display_order_sequential(self):
        orders = [item["display_order"] for item in PINK_TEAM_CHECKLIST]
        assert orders == list(range(1, len(PINK_TEAM_CHECKLIST) + 1))

    def test_categories_present(self):
        categories = {item["category"] for item in PINK_TEAM_CHECKLIST}
        assert "Story & Themes" in categories
        assert "Responsiveness" in categories
        assert "Content Quality" in categories


class TestRedTeamChecklist:
    def test_has_items(self):
        assert len(RED_TEAM_CHECKLIST) > 0

    def test_all_items_have_required_keys(self):
        for item in RED_TEAM_CHECKLIST:
            assert "category" in item
            assert "item_text" in item
            assert "display_order" in item

    def test_display_order_sequential(self):
        orders = [item["display_order"] for item in RED_TEAM_CHECKLIST]
        assert orders == list(range(1, len(RED_TEAM_CHECKLIST) + 1))

    def test_categories_present(self):
        categories = {item["category"] for item in RED_TEAM_CHECKLIST}
        assert "Compliance" in categories
        assert "Format" in categories
        assert "Evaluation Criteria" in categories


class TestGoldTeamChecklist:
    def test_has_items(self):
        assert len(GOLD_TEAM_CHECKLIST) > 0

    def test_all_items_have_required_keys(self):
        for item in GOLD_TEAM_CHECKLIST:
            assert "category" in item
            assert "item_text" in item
            assert "display_order" in item

    def test_display_order_sequential(self):
        orders = [item["display_order"] for item in GOLD_TEAM_CHECKLIST]
        assert orders == list(range(1, len(GOLD_TEAM_CHECKLIST) + 1))

    def test_categories_present(self):
        categories = {item["category"] for item in GOLD_TEAM_CHECKLIST}
        assert "Win Strategy" in categories
        assert "Risk Assessment" in categories
        assert "Go/No-Go" in categories
