"""
Draft Benchmark Unit Tests
============================
Tests for score_section_text(), generate_recommendations(), BenchmarkScore.
"""

from app.services.draft_benchmark import (
    BENCHMARK_SCENARIOS,
    CITATION_KEYWORDS,
    BenchmarkScore,
    generate_recommendations,
    score_section_text,
)

# =============================================================================
# BenchmarkScore
# =============================================================================


class TestBenchmarkScore:
    def test_pink_team_ready_high_scores(self):
        bs = BenchmarkScore(
            section_name="Tech",
            compliance_coverage=80,
            specificity=70,
            citation_density=60,
            readability=65,
            structure_score=55,
            overall=72,
        )
        assert bs.is_pink_team_ready is True

    def test_not_ready_low_overall(self):
        bs = BenchmarkScore(
            section_name="Tech",
            compliance_coverage=80,
            specificity=70,
            citation_density=60,
            readability=65,
            structure_score=55,
            overall=65,
        )
        assert bs.is_pink_team_ready is False

    def test_not_ready_category_below_50(self):
        bs = BenchmarkScore(
            section_name="Tech",
            compliance_coverage=80,
            specificity=70,
            citation_density=40,  # below 50
            readability=65,
            structure_score=55,
            overall=72,
        )
        assert bs.is_pink_team_ready is False


# =============================================================================
# score_section_text
# =============================================================================


class TestScoreSectionText:
    def test_returns_benchmark_score(self):
        text = "Our technical approach leverages proven NIST frameworks. We have 5 years of experience delivering cloud migration services with 99.9% uptime SLAs."
        result = score_section_text("Technical Approach", text, ["cloud migration", "NIST"])
        assert isinstance(result, BenchmarkScore)
        assert result.section_name == "Technical Approach"

    def test_all_scores_in_range(self):
        text = "Generic proposal text with some details about our approach to solving the problem."
        result = score_section_text("Section", text, ["approach"])
        assert 0 <= result.compliance_coverage <= 100
        assert 0 <= result.specificity <= 100
        assert 0 <= result.citation_density <= 100
        assert 0 <= result.readability <= 100
        assert 0 <= result.structure_score <= 100
        assert 0 <= result.overall <= 100

    def test_high_citation_density(self):
        text = "Per NIST 800-53, our ISO 27001 certified team follows FAR compliance. CMMC Level 2 demonstrated through proven FedRAMP authorization."
        result = score_section_text("Section", text, [])
        assert result.citation_density > 0

    def test_structure_headings_and_lists(self):
        text = """# Technical Approach

Our approach includes:
- Phase 1: Discovery
- Phase 2: Implementation
- Phase 3: Deployment

## Management Plan

1. Risk identification
2. Mitigation strategies"""
        result = score_section_text("Section", text, [])
        assert result.structure_score > 0

    def test_empty_text_does_not_crash(self):
        result = score_section_text("Section", "", [])
        assert isinstance(result, BenchmarkScore)


# =============================================================================
# generate_recommendations
# =============================================================================


class TestGenerateRecommendations:
    def test_all_good(self):
        scores = [
            BenchmarkScore("A", 90, 80, 75, 80, 70, 80),
        ]
        recs = generate_recommendations(scores)
        assert len(recs) == 1
        assert "meet" in recs[0].lower() or "threshold" in recs[0].lower()

    def test_low_compliance(self):
        scores = [BenchmarkScore("A", 40, 80, 75, 80, 70, 60)]
        recs = generate_recommendations(scores)
        assert any("traceability" in r.lower() or "requirement" in r.lower() for r in recs)

    def test_low_specificity(self):
        scores = [BenchmarkScore("A", 80, 30, 75, 80, 70, 60)]
        recs = generate_recommendations(scores)
        assert any("quantitative" in r.lower() or "metrics" in r.lower() for r in recs)

    def test_low_citations(self):
        scores = [BenchmarkScore("A", 80, 70, 30, 80, 70, 60)]
        recs = generate_recommendations(scores)
        assert any("standards" in r.lower() or "cite" in r.lower() for r in recs)

    def test_low_readability(self):
        scores = [BenchmarkScore("A", 80, 70, 70, 30, 70, 60)]
        recs = generate_recommendations(scores)
        assert any("sentence" in r.lower() or "reading level" in r.lower() for r in recs)

    def test_low_structure(self):
        scores = [BenchmarkScore("A", 80, 70, 70, 80, 30, 60)]
        recs = generate_recommendations(scores)
        assert any("structure" in r.lower() or "heading" in r.lower() for r in recs)


# =============================================================================
# Constants
# =============================================================================


class TestBenchmarkConstants:
    def test_scenarios_have_sections(self):
        for scenario in BENCHMARK_SCENARIOS:
            assert "rfp_type" in scenario
            assert "sections" in scenario
            assert "key_requirements" in scenario
            assert len(scenario["sections"]) > 0

    def test_citation_keywords_populated(self):
        assert len(CITATION_KEYWORDS) > 5
