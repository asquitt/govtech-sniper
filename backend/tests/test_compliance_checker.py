"""
Compliance Checker Unit Tests
==============================
Tests for FARComplianceChecker and AIQualityScorer.
Pure-logic tests, no AI dependency.
"""

from app.services.compliance_checker import (
    AIQualityScorer,
    ComplianceLevel,
    FARComplianceChecker,
)

# =============================================================================
# FARComplianceChecker
# =============================================================================


class TestFARComplianceChecker:
    def setup_method(self):
        self.checker = FARComplianceChecker()

    def test_fully_compliant_proposal(self):
        """Proposal mentioning all keywords should have no/minimal issues."""
        text = """
        We certify and represent our compliance with all FAR requirements.
        Our key personnel include the Program Manager with 15 years experience.
        Past performance references include Contract W911QY-20-C-0001 in CPARS.
        Our price proposal follows the specified labor rate format.
        Our technical approach and methodology addresses all SOW requirements.
        Our subcontracting plan includes small business goals.
        We have no organizational conflict of interest (OCI).
        All personnel hold Secret security clearance.
        Deliverable milestones and schedule are in Section 3.
        Our quality assurance (QA) process follows ISO 9001.
        """
        report = self.checker.check_proposal(text)
        assert report.critical_count == 0
        assert report.passed is True
        assert report.compliance_score >= 60

    def test_empty_proposal_flags_issues(self):
        report = self.checker.check_proposal("")
        assert report.total_issues > 0
        assert report.critical_count > 0
        assert report.passed is False

    def test_missing_certification_is_critical(self):
        # Text with no certification keywords
        text = "This is a generic proposal about cyber security work."
        report = self.checker.check_proposal(text)
        cert_issues = [i for i in report.issues if i.rule_id == "CERT-001"]
        assert len(cert_issues) == 1
        assert cert_issues[0].level == ComplianceLevel.CRITICAL

    def test_missing_price_is_critical(self):
        text = "Our team will deliver excellent technical work with certified experts."
        report = self.checker.check_proposal(text)
        price_issues = [i for i in report.issues if i.rule_id == "PRICE-001"]
        assert len(price_issues) == 1
        assert price_issues[0].level == ComplianceLevel.CRITICAL

    def test_far_clause_checking(self):
        text = "We are registered in sam.gov and use electronic funds transfer."
        report = self.checker.check_proposal(text, rfp_clauses=["52.204-7", "52.232-33"])
        # Both clauses should be addressed
        far_issues = [i for i in report.issues if i.rule_id.startswith("FAR-")]
        assert len(far_issues) == 0

    def test_unaddressed_far_clause(self):
        text = "Our team has extensive experience."
        report = self.checker.check_proposal(text, rfp_clauses=["52.204-7"])
        far_issues = [i for i in report.issues if i.rule_id == "FAR-52.204-7"]
        assert len(far_issues) == 1

    def test_subcontracting_required_over_750k(self):
        text = "Our technical approach covers all requirements with key personnel. We certify compliance with pricing."
        report = self.checker.check_proposal(text, contract_value=1_000_000)
        sub_issues = [i for i in report.issues if i.rule_id == "SUB-002"]
        assert len(sub_issues) == 1
        assert sub_issues[0].level == ComplianceLevel.CRITICAL

    def test_cas_warning_over_2m(self):
        text = "Our certified pricing proposal with key personnel and subcontracting plan."
        report = self.checker.check_proposal(text, contract_value=3_000_000)
        cas_issues = [i for i in report.issues if i.rule_id == "COST-001"]
        assert len(cas_issues) == 1
        assert cas_issues[0].level == ComplianceLevel.WARNING

    def test_compliance_score_clamped_0_100(self):
        # Lots of issues should still produce score >= 0
        report = self.checker.check_proposal("")
        assert 0 <= report.compliance_score <= 100

    def test_get_required_clauses_extracts_patterns(self):
        rfp_text = """
        This RFP incorporates FAR 52.204-7, FAR 52.219-1, and 52.222-26.
        Also applicable: 52.225-25 and FAR 52.232-33.
        """
        clauses = self.checker.get_required_clauses(rfp_text)
        assert "52.204-7" in clauses
        assert "52.219-1" in clauses
        assert "52.222-26" in clauses
        assert len(clauses) >= 4


# =============================================================================
# AIQualityScorer
# =============================================================================


class TestAIQualityScorer:
    def setup_method(self):
        self.scorer = AIQualityScorer()

    def test_high_quality_content(self):
        content = """
        Our team achieved a 99.7% uptime for the DoD network operations center,
        delivering all 12 milestones ahead of schedule. We implemented zero-trust
        architecture that reduced security incidents by 45% in the first quarter.
        [[Source: CPARS Rating FY2023]] Our program manager led a team of 25 engineers
        who completed NIST 800-53 compliance assessments. We managed a $4.2M budget
        and delivered cost savings of $850K through process automation.
        [[Source: Contract W911QY-20-C-0001]] Our methodology includes weekly sprint
        reviews and monthly progress reports. We built custom dashboards that improved
        stakeholder visibility by 60%. [[Source: Past Performance Questionnaire]]
        """
        result = self.scorer.score_content(content)
        assert result["overall_score"] >= 60
        assert result["rating"] in ("Excellent", "Good", "Fair")
        assert result["metrics"]["word_count"] > 50

    def test_low_quality_vague_content(self):
        content = "Various innovative solutions. Significant experience. Best-in-class cutting-edge robust leverage."
        result = self.scorer.score_content(content)
        assert result["metrics"]["vague_phrase_count"] > 3
        assert result["breakdown"]["specificity"] < 80

    def test_needs_source_markers_reduce_score(self):
        content = "We delivered 99% uptime [NEEDS SOURCE]. Revenue grew 30% [NEEDS SOURCE]."
        result = self.scorer.score_content(content)
        assert result["metrics"]["needs_source_count"] == 2

    def test_requirement_coverage(self):
        requirement = "Provide cybersecurity monitoring and incident response capabilities"
        content = "Our cybersecurity monitoring team provides 24/7 incident response capabilities using advanced SIEM tools."
        result = self.scorer.score_content(content, requirement_text=requirement)
        assert result["breakdown"]["requirement_coverage"] >= 60

    def test_short_content_length_penalty(self):
        content = "We will do the work."
        result = self.scorer.score_content(content)
        assert result["breakdown"]["length"] <= 70

    def test_returns_suggestions(self):
        content = "We will do stuff."
        result = self.scorer.score_content(content)
        assert isinstance(result["suggestions"], list)
        assert len(result["suggestions"]) > 0
