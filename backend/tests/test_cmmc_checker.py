"""
CMMC Checker Unit Tests
========================
Tests for CMMC compliance scoring and NIST overview — pure computation, no I/O.
"""

from app.services.cmmc_checker import (
    DOMAIN_NAMES,
    CMMCControl,
    CMMCDomain,
    get_cmmc_controls,
    get_compliance_score,
    get_nist_overview,
)
from app.services.review_checklist_templates import (
    GOLD_TEAM_CHECKLIST,
    PINK_TEAM_CHECKLIST,
    RED_TEAM_CHECKLIST,
    get_checklist_template,
)

# =============================================================================
# CMMC Controls
# =============================================================================


class TestGetCMMCControls:
    def test_returns_list(self):
        controls = get_cmmc_controls()
        assert isinstance(controls, list)
        assert len(controls) > 0

    def test_returns_copies(self):
        """Returned list is a new list (not the module-level reference)."""
        a = get_cmmc_controls()
        b = get_cmmc_controls()
        assert a is not b

    def test_all_are_cmmc_controls(self):
        for c in get_cmmc_controls():
            assert isinstance(c, CMMCControl)
            assert isinstance(c.domain, CMMCDomain)
            assert c.level in (1, 2)


class TestCMMCDomainNames:
    def test_all_domains_have_names(self):
        for domain in CMMCDomain:
            assert domain in DOMAIN_NAMES
            assert isinstance(DOMAIN_NAMES[domain], str)
            assert len(DOMAIN_NAMES[domain]) > 0


# =============================================================================
# Compliance Scoring
# =============================================================================


class TestGetComplianceScore:
    def test_structure(self):
        score = get_compliance_score()
        assert "total_controls" in score
        assert "met_controls" in score
        assert "score_percentage" in score
        assert "target_level" in score
        assert "domains" in score

    def test_math_consistency(self):
        score = get_compliance_score()
        assert score["met_controls"] <= score["total_controls"]
        expected_pct = round(score["met_controls"] / score["total_controls"] * 100)
        assert score["score_percentage"] == expected_pct

    def test_domains_cover_all_controls(self):
        score = get_compliance_score()
        domain_total = sum(d["total_controls"] for d in score["domains"])
        assert domain_total == score["total_controls"]

    def test_domain_percentages(self):
        score = get_compliance_score()
        for d in score["domains"]:
            if d["total_controls"] > 0:
                expected = round(d["met_controls"] / d["total_controls"] * 100)
                assert d["percentage"] == expected

    def test_domains_sorted_by_code(self):
        score = get_compliance_score()
        codes = [d["domain"] for d in score["domains"]]
        assert codes == sorted(codes)


# =============================================================================
# NIST Overview
# =============================================================================


class TestGetNISTOverview:
    def test_structure(self):
        overview = get_nist_overview()
        assert overview["framework"] == "NIST 800-53 Rev 5"
        assert "total_families" in overview
        assert "families" in overview
        assert "overall_coverage" in overview

    def test_family_count(self):
        overview = get_nist_overview()
        assert overview["total_families"] == len(overview["families"])

    def test_coverage_calculation(self):
        overview = get_nist_overview()
        total_impl = sum(f["implemented"] for f in overview["families"])
        total_all = sum(f["total_controls"] for f in overview["families"])
        assert overview["overall_coverage"] == round(total_impl / total_all * 100)

    def test_family_fields(self):
        overview = get_nist_overview()
        for f in overview["families"]:
            assert "family_id" in f
            assert "name" in f
            assert "total_controls" in f
            assert "implemented" in f
            assert f["implemented"] <= f["total_controls"]


# =============================================================================
# Review Checklist Templates
# =============================================================================


class TestGetChecklistTemplate:
    def test_pink_team(self):
        template = get_checklist_template("pink")
        assert template is PINK_TEAM_CHECKLIST
        assert len(template) > 0

    def test_red_team(self):
        template = get_checklist_template("red")
        assert template is RED_TEAM_CHECKLIST
        assert len(template) > 0

    def test_gold_team(self):
        template = get_checklist_template("gold")
        assert template is GOLD_TEAM_CHECKLIST
        assert len(template) > 0

    def test_unknown_returns_empty(self):
        assert get_checklist_template("purple") == []

    def test_checklist_item_structure(self):
        for review_type in ("pink", "red", "gold"):
            for item in get_checklist_template(review_type):
                assert "category" in item
                assert "item_text" in item
                assert "display_order" in item

    def test_display_order_sequential(self):
        for review_type in ("pink", "red", "gold"):
            orders = [item["display_order"] for item in get_checklist_template(review_type)]
            assert orders == sorted(orders)
            assert orders[0] == 1
