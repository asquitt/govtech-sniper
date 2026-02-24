"""
Workflow Engine Unit Tests
===========================
Tests for pure helper functions: _to_float, _match_condition, _rule_matches.
No database or async — only deterministic logic.
"""

from unittest.mock import MagicMock

from app.services.workflow_engine import _match_condition, _rule_matches, _to_float

# =============================================================================
# _to_float
# =============================================================================


class TestToFloat:
    def test_int(self):
        assert _to_float(42) == 42.0

    def test_float(self):
        assert _to_float(3.14) == 3.14

    def test_string_number(self):
        assert _to_float("99.5") == 99.5

    def test_none(self):
        assert _to_float(None) is None

    def test_non_numeric_string(self):
        assert _to_float("abc") is None

    def test_empty_string(self):
        assert _to_float("") is None


# =============================================================================
# _match_condition
# =============================================================================


class TestMatchCondition:
    # --- equals ---
    def test_equals_match(self):
        assert _match_condition("active", "equals", "active") is True

    def test_equals_mismatch(self):
        assert _match_condition("active", "equals", "closed") is False

    # --- gt ---
    def test_gt_true(self):
        assert _match_condition(100, "gt", 50) is True

    def test_gt_false(self):
        assert _match_condition(30, "gt", 50) is False

    def test_gt_with_none(self):
        assert _match_condition(None, "gt", 50) is False

    # --- lt ---
    def test_lt_true(self):
        assert _match_condition(10, "lt", 50) is True

    def test_lt_false(self):
        assert _match_condition(100, "lt", 50) is False

    # --- contains ---
    def test_contains_string(self):
        assert _match_condition("cybersecurity services", "contains", "cyber") is True

    def test_contains_string_miss(self):
        assert _match_condition("IT services", "contains", "cyber") is False

    def test_contains_list(self):
        assert _match_condition(["a", "b", "c"], "contains", "b") is True

    def test_contains_list_miss(self):
        assert _match_condition(["a", "b"], "contains", "z") is False

    def test_contains_none(self):
        assert _match_condition(None, "contains", "x") is False

    # --- in_list ---
    def test_in_list_true(self):
        assert _match_condition("DoD", "in_list", ["DoD", "GSA", "VA"]) is True

    def test_in_list_false(self):
        assert _match_condition("NASA", "in_list", ["DoD", "GSA"]) is False

    def test_in_list_non_list_expected(self):
        assert _match_condition("x", "in_list", "not a list") is False

    # --- unknown operator ---
    def test_unknown_operator(self):
        assert _match_condition("x", "regex", "x") is False


# =============================================================================
# _rule_matches
# =============================================================================


def _mock_rule(conditions):
    rule = MagicMock()
    rule.conditions = conditions
    return rule


class TestRuleMatches:
    def test_empty_conditions_matches(self):
        assert _rule_matches(_mock_rule(None), {}) is True
        assert _rule_matches(_mock_rule([]), {}) is True

    def test_single_condition_match(self):
        rule = _mock_rule([{"field": "status", "operator": "equals", "value": "active"}])
        assert _rule_matches(rule, {"status": "active"}) is True

    def test_single_condition_miss(self):
        rule = _mock_rule([{"field": "status", "operator": "equals", "value": "active"}])
        assert _rule_matches(rule, {"status": "closed"}) is False

    def test_all_conditions_must_match(self):
        rule = _mock_rule(
            [
                {"field": "status", "operator": "equals", "value": "active"},
                {"field": "score", "operator": "gt", "value": 50},
            ]
        )
        assert _rule_matches(rule, {"status": "active", "score": 80}) is True
        assert _rule_matches(rule, {"status": "active", "score": 30}) is False

    def test_missing_field_fails(self):
        rule = _mock_rule([{"field": "missing", "operator": "equals", "value": "x"}])
        assert _rule_matches(rule, {"other": "y"}) is False
