"""
AI Draft Quality Benchmarking Service
=====================================
Scores generated proposal sections against pink-team readiness criteria
used by government proposal reviewers.
"""

import re
from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class BenchmarkScore:
    """Score for a single proposal section."""

    section_name: str
    compliance_coverage: float  # 0-100: Does it address all RFP requirements?
    specificity: float  # 0-100: Concrete details vs vague promises?
    citation_density: float  # 0-100: References to past performance, standards, etc.
    readability: float  # 0-100: Flesch-Kincaid appropriate for gov audience?
    structure_score: float  # 0-100: Proper headings, paragraphs, lists?
    overall: float  # Weighted average

    @property
    def is_pink_team_ready(self) -> bool:
        """Pink team ready means overall >= 70 and no category below 50."""
        return self.overall >= 70 and all(
            [
                self.compliance_coverage >= 50,
                self.specificity >= 50,
                self.citation_density >= 50,
                self.readability >= 50,
                self.structure_score >= 50,
            ]
        )


@dataclass
class BenchmarkResult:
    """Full benchmark result for a proposal."""

    rfp_type: str  # e.g., "IT Services", "Professional Services"
    sections: list[BenchmarkScore]
    overall_score: float
    pink_team_ready: bool
    recommendations: list[str]


# Benchmark RFP scenarios for testing
BENCHMARK_SCENARIOS = [
    {
        "rfp_type": "IT Services",
        "title": "Cloud Migration and Modernization Services",
        "sections": [
            "Technical Approach",
            "Management Approach",
            "Past Performance",
            "Staffing Plan",
        ],
        "key_requirements": [
            "FedRAMP compliance",
            "Agile methodology",
            "Transition plan from legacy systems",
            "24/7 NOC support",
        ],
    },
    {
        "rfp_type": "Professional Services",
        "title": "Program Management Office Support",
        "sections": [
            "Technical Approach",
            "Management Approach",
            "Past Performance",
            "Quality Control",
        ],
        "key_requirements": [
            "PMP-certified staff",
            "Earned Value Management",
            "Risk management framework",
            "Stakeholder communication plan",
        ],
    },
    {
        "rfp_type": "Construction",
        "title": "Military Base Facility Renovation",
        "sections": [
            "Technical Approach",
            "Safety Plan",
            "Past Performance",
            "Schedule",
        ],
        "key_requirements": [
            "Davis-Bacon Act compliance",
            "OSHA safety standards",
            "Environmental impact assessment",
            "Phased construction timeline",
        ],
    },
    {
        "rfp_type": "R&D",
        "title": "Advanced AI/ML Research for Defense Applications",
        "sections": [
            "Technical Approach",
            "Research Methodology",
            "Past Performance",
            "Data Management",
        ],
        "key_requirements": [
            "CMMC Level 2 compliance",
            "Responsible AI principles",
            "Peer-reviewed publication plan",
            "Technology Readiness Level progression",
        ],
    },
    {
        "rfp_type": "Logistics",
        "title": "Supply Chain Management and Distribution Services",
        "sections": [
            "Technical Approach",
            "Management Approach",
            "Past Performance",
            "Contingency Plan",
        ],
        "key_requirements": [
            "Just-in-time delivery capability",
            "RFID tracking implementation",
            "Disaster recovery logistics",
            "Small business subcontracting plan",
        ],
    },
]


CITATION_KEYWORDS = [
    "ISO",
    "NIST",
    "FAR",
    "DFAR",
    "CMMC",
    "FedRAMP",
    "PMP",
    "ITIL",
    "demonstrated",
    "proven",
    "delivered",
    "successfully",
    "experience",
    "case study",
    "contract",
    "award",
    "performance",
]


def score_section_text(section_name: str, text: str, requirements: list[str]) -> BenchmarkScore:
    """Score a generated section against pink-team criteria."""
    word_count = len(text.split())
    sentence_count = len(re.findall(r"[.!?]+", text)) or 1
    paragraph_count = len([p for p in text.split("\n\n") if p.strip()]) or 1

    # Compliance coverage: check how many requirements are addressed
    req_hits = sum(
        1 for req in requirements if any(kw.lower() in text.lower() for kw in req.split()[:3])
    )
    compliance = (req_hits / max(len(requirements), 1)) * 100

    # Specificity: measure concrete details (numbers, dates, percentages, metrics)
    specifics = len(re.findall(r"\b\d+[%]?\b", text))
    specificity = min(100, (specifics / max(word_count / 100, 1)) * 50)

    # Citation density: references to standards, frameworks, past work
    cite_hits = sum(1 for kw in CITATION_KEYWORDS if kw.lower() in text.lower())
    citation = min(100, (cite_hits / 5) * 50)

    # Readability: Flesch-Kincaid approximation (gov writing ~grade 12-14)
    avg_sentence_len = word_count / sentence_count
    syllable_count = sum(max(1, len(re.findall(r"[aeiouy]+", w.lower()))) for w in text.split())
    avg_syllables = syllable_count / max(word_count, 1)
    fk_grade = 0.39 * avg_sentence_len + 11.8 * avg_syllables - 15.59
    # Score: best at grade 12-14, drops off outside
    grade_diff = abs(fk_grade - 13)
    readability = max(0, min(100, 100 - grade_diff * 10))

    # Structure: headings, paragraphs, lists
    has_headings = bool(re.findall(r"^#{1,3}\s|^[A-Z][A-Za-z\s]{5,}:", text, re.MULTILINE))
    has_lists = bool(re.findall(r"^\s*[-\u2022*]\s|^\s*\d+[.)]\s", text, re.MULTILINE))
    structure = 0.0
    structure += 30 if has_headings else 0
    structure += 30 if has_lists else 0
    structure += min(40, paragraph_count * 10)

    # Weighted overall
    overall = (
        compliance * 0.30
        + specificity * 0.20
        + citation * 0.20
        + readability * 0.15
        + structure * 0.15
    )

    return BenchmarkScore(
        section_name=section_name,
        compliance_coverage=round(compliance, 1),
        specificity=round(specificity, 1),
        citation_density=round(citation, 1),
        readability=round(readability, 1),
        structure_score=round(structure, 1),
        overall=round(overall, 1),
    )


def generate_recommendations(scores: list[BenchmarkScore]) -> list[str]:
    """Generate improvement recommendations based on scores."""
    recs: list[str] = []
    count = max(len(scores), 1)
    avg_compliance = sum(s.compliance_coverage for s in scores) / count
    avg_specificity = sum(s.specificity for s in scores) / count
    avg_citations = sum(s.citation_density for s in scores) / count
    avg_readability = sum(s.readability for s in scores) / count
    avg_structure = sum(s.structure_score for s in scores) / count

    if avg_compliance < 70:
        recs.append(
            "Improve requirement traceability -- add explicit callouts to each RFP requirement"
        )
    if avg_specificity < 60:
        recs.append("Add more quantitative details -- metrics, timelines, team sizes, SLA targets")
    if avg_citations < 60:
        recs.append("Increase standards references -- cite NIST, FAR, ISO frameworks by number")
    if avg_readability < 60:
        recs.append(
            "Simplify sentence structure -- target grade 12-14 reading level for gov reviewers"
        )
    if avg_structure < 60:
        recs.append(
            "Improve document structure -- add section headings, bullet lists, and numbered steps"
        )

    if not recs:
        recs.append("All quality dimensions meet pink-team readiness thresholds")

    return recs
