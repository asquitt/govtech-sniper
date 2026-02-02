"""
RFP Sniper - FAR/DFAR Compliance Checker
=========================================
Check proposals for compliance with Federal Acquisition Regulations.
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class ComplianceLevel(str, Enum):
    """Compliance check severity levels."""
    CRITICAL = "critical"    # Must fix - will cause rejection
    WARNING = "warning"      # Should fix - may cause issues
    INFO = "info"           # Suggestion for improvement


@dataclass
class ComplianceIssue:
    """A compliance issue found in the proposal."""
    rule_id: str
    rule_name: str
    level: ComplianceLevel
    description: str
    section: Optional[str] = None
    suggestion: Optional[str] = None
    far_reference: Optional[str] = None


@dataclass
class ComplianceReport:
    """Full compliance check report."""
    total_issues: int
    critical_count: int
    warning_count: int
    info_count: int
    issues: List[ComplianceIssue]
    compliance_score: float  # 0-100
    passed: bool


class FARComplianceChecker:
    """
    Check proposals for FAR (Federal Acquisition Regulation) compliance.

    Checks include:
    - Required representations and certifications
    - Pricing format requirements
    - Small business subcontracting plans
    - Organizational conflict of interest
    - Key personnel requirements
    - And more...
    """

    # Common FAR clauses and their requirements
    FAR_CLAUSES = {
        "52.204-7": {
            "name": "System for Award Management",
            "requirement": "Active SAM registration",
            "keywords": ["sam.gov", "sam registration", "system for award management"],
        },
        "52.219-1": {
            "name": "Small Business Program Representations",
            "requirement": "Small business size standard representation",
            "keywords": ["small business", "size standard", "naics"],
        },
        "52.222-26": {
            "name": "Equal Opportunity",
            "requirement": "Equal opportunity clause compliance",
            "keywords": ["equal opportunity", "eeo", "non-discrimination"],
        },
        "52.223-6": {
            "name": "Drug-Free Workplace",
            "requirement": "Drug-free workplace certification",
            "keywords": ["drug-free", "substance abuse"],
        },
        "52.225-25": {
            "name": "Buy American",
            "requirement": "Buy American Act compliance",
            "keywords": ["buy american", "domestic preference", "made in usa"],
        },
        "52.232-33": {
            "name": "Payment by EFT",
            "requirement": "Electronic funds transfer capability",
            "keywords": ["eft", "electronic funds transfer", "ach"],
        },
    }

    # Common compliance checks
    COMPLIANCE_CHECKS = [
        {
            "id": "CERT-001",
            "name": "Representations and Certifications",
            "level": ComplianceLevel.CRITICAL,
            "check": lambda text: any(kw in text.lower() for kw in [
                "certif", "represent", "attest", "affirm"
            ]),
            "description": "Proposal should include required certifications and representations",
            "suggestion": "Add a section explicitly addressing required FAR certifications",
            "far_reference": "FAR 52.204-8",
        },
        {
            "id": "KEY-001",
            "name": "Key Personnel Identification",
            "level": ComplianceLevel.WARNING,
            "check": lambda text: any(kw in text.lower() for kw in [
                "key personnel", "project manager", "program manager", "key staff"
            ]),
            "description": "Key personnel should be clearly identified with qualifications",
            "suggestion": "Include resumes and qualifications for all key personnel",
            "far_reference": "FAR 15.305(a)(2)",
        },
        {
            "id": "PP-001",
            "name": "Past Performance References",
            "level": ComplianceLevel.WARNING,
            "check": lambda text: any(kw in text.lower() for kw in [
                "past performance", "contract reference", "cpars", "prior experience"
            ]),
            "description": "Past performance should include verifiable references",
            "suggestion": "Include contract numbers, POCs, and CPARS ratings",
            "far_reference": "FAR 15.305(a)(2)",
        },
        {
            "id": "PRICE-001",
            "name": "Price/Cost Information",
            "level": ComplianceLevel.CRITICAL,
            "check": lambda text: any(kw in text.lower() for kw in [
                "price", "cost", "labor rate", "pricing"
            ]),
            "description": "Price/cost volume should be clearly separated and formatted",
            "suggestion": "Ensure pricing follows solicitation format requirements",
            "far_reference": "FAR 15.403",
        },
        {
            "id": "TECH-001",
            "name": "Technical Approach",
            "level": ComplianceLevel.WARNING,
            "check": lambda text: any(kw in text.lower() for kw in [
                "technical approach", "methodology", "approach", "solution"
            ]),
            "description": "Technical approach should address all SOW requirements",
            "suggestion": "Ensure technical approach maps to each SOW requirement",
            "far_reference": "FAR 15.305(a)(3)",
        },
        {
            "id": "SUB-001",
            "name": "Subcontracting Plan",
            "level": ComplianceLevel.WARNING,
            "check": lambda text: any(kw in text.lower() for kw in [
                "subcontract", "teaming", "subcontracting plan"
            ]),
            "description": "Subcontracting plan may be required for contracts > $750K",
            "suggestion": "Include small business subcontracting goals if applicable",
            "far_reference": "FAR 19.702",
        },
        {
            "id": "OCI-001",
            "name": "Organizational Conflict of Interest",
            "level": ComplianceLevel.WARNING,
            "check": lambda text: any(kw in text.lower() for kw in [
                "conflict of interest", "oci", "organizational conflict"
            ]),
            "description": "Address potential organizational conflicts of interest",
            "suggestion": "Include OCI mitigation plan if applicable",
            "far_reference": "FAR 9.5",
        },
        {
            "id": "SEC-001",
            "name": "Security Requirements",
            "level": ComplianceLevel.CRITICAL,
            "check": lambda text: any(kw in text.lower() for kw in [
                "clearance", "security", "classified", "cui"
            ]),
            "description": "Security requirements should be clearly addressed",
            "suggestion": "Document clearance levels and security compliance",
            "far_reference": "FAR 4.4",
        },
        {
            "id": "DEL-001",
            "name": "Deliverables Schedule",
            "level": ComplianceLevel.WARNING,
            "check": lambda text: any(kw in text.lower() for kw in [
                "deliverable", "milestone", "schedule", "timeline"
            ]),
            "description": "Deliverables should include clear schedules",
            "suggestion": "Provide specific dates or durations for all deliverables",
            "far_reference": "FAR 11.4",
        },
        {
            "id": "QA-001",
            "name": "Quality Assurance",
            "level": ComplianceLevel.WARNING,
            "check": lambda text: any(kw in text.lower() for kw in [
                "quality", "qa", "quality assurance", "quality control"
            ]),
            "description": "Quality assurance plan should be included",
            "suggestion": "Document QA processes and metrics",
            "far_reference": "FAR 46.2",
        },
    ]

    def check_proposal(
        self,
        proposal_text: str,
        rfp_clauses: List[str] = None,
        contract_value: int = None,
    ) -> ComplianceReport:
        """
        Run compliance checks on a proposal.

        Args:
            proposal_text: Full text of the proposal
            rfp_clauses: List of FAR clause numbers from the RFP
            contract_value: Estimated contract value (affects some requirements)

        Returns:
            ComplianceReport with all findings
        """
        issues = []
        text_lower = proposal_text.lower()

        # Run standard checks
        for check in self.COMPLIANCE_CHECKS:
            check_func = check["check"]

            # If check returns False, there's a potential issue
            if not check_func(proposal_text):
                issues.append(ComplianceIssue(
                    rule_id=check["id"],
                    rule_name=check["name"],
                    level=check["level"],
                    description=check["description"],
                    suggestion=check.get("suggestion"),
                    far_reference=check.get("far_reference"),
                ))

        # Check for specific FAR clause references if provided
        if rfp_clauses:
            for clause in rfp_clauses:
                clause_info = self.FAR_CLAUSES.get(clause)
                if clause_info:
                    # Check if clause is addressed
                    keywords = clause_info.get("keywords", [])
                    if not any(kw in text_lower for kw in keywords):
                        issues.append(ComplianceIssue(
                            rule_id=f"FAR-{clause}",
                            rule_name=clause_info["name"],
                            level=ComplianceLevel.WARNING,
                            description=f"FAR clause {clause} may not be addressed",
                            suggestion=clause_info["requirement"],
                            far_reference=f"FAR {clause}",
                        ))

        # Additional checks based on contract value
        if contract_value:
            # Subcontracting plan required for > $750K
            if contract_value > 750000:
                if "subcontracting plan" not in text_lower:
                    issues.append(ComplianceIssue(
                        rule_id="SUB-002",
                        rule_name="Small Business Subcontracting Plan Required",
                        level=ComplianceLevel.CRITICAL,
                        description=f"Contracts over $750K require small business subcontracting plan",
                        suggestion="Include a detailed subcontracting plan with goals",
                        far_reference="FAR 19.702",
                    ))

            # Cost/pricing data for > $2M
            if contract_value > 2000000:
                if not any(kw in text_lower for kw in ["cost accounting", "cas", "dcaa"]):
                    issues.append(ComplianceIssue(
                        rule_id="COST-001",
                        rule_name="Cost Accounting Standards",
                        level=ComplianceLevel.WARNING,
                        description="Contracts over $2M may require CAS compliance",
                        suggestion="Address Cost Accounting Standards applicability",
                        far_reference="FAR 30.201-4",
                    ))

        # Count by severity
        critical_count = len([i for i in issues if i.level == ComplianceLevel.CRITICAL])
        warning_count = len([i for i in issues if i.level == ComplianceLevel.WARNING])
        info_count = len([i for i in issues if i.level == ComplianceLevel.INFO])

        # Calculate compliance score
        # Critical issues: -20 points each
        # Warning issues: -5 points each
        # Info issues: -1 point each
        score = 100 - (critical_count * 20) - (warning_count * 5) - (info_count * 1)
        score = max(0, min(100, score))

        # Determine pass/fail
        passed = critical_count == 0 and score >= 60

        return ComplianceReport(
            total_issues=len(issues),
            critical_count=critical_count,
            warning_count=warning_count,
            info_count=info_count,
            issues=issues,
            compliance_score=score,
            passed=passed,
        )

    def get_required_clauses(self, rfp_text: str) -> List[str]:
        """
        Extract FAR clause references from RFP text.

        Args:
            rfp_text: Full RFP text

        Returns:
            List of FAR clause numbers
        """
        # Pattern for FAR clauses: FAR 52.xxx-xx or 52.xxx-xx
        pattern = r'(?:FAR\s+)?52\.\d{3}-\d+'
        matches = re.findall(pattern, rfp_text, re.IGNORECASE)

        # Clean and deduplicate
        clauses = list(set(
            m.replace("FAR ", "").replace("far ", "").strip()
            for m in matches
        ))

        logger.info(f"Found {len(clauses)} FAR clause references")
        return clauses


class AIQualityScorer:
    """
    Score the quality of AI-generated proposal content.

    Factors:
    - Citation coverage (claims backed by sources)
    - Requirement coverage
    - Writing quality
    - Specificity (concrete vs vague)
    """

    # Vague phrases that should be avoided
    VAGUE_PHRASES = [
        "various", "many", "some", "several",
        "significant", "substantial", "considerable",
        "best-in-class", "world-class", "cutting-edge",
        "state-of-the-art", "innovative", "robust",
        "leverage", "synergy", "paradigm",
        "as needed", "if required", "when necessary",
    ]

    # Strong verbs for proposals
    STRONG_VERBS = [
        "achieved", "delivered", "implemented", "completed",
        "reduced", "increased", "improved", "saved",
        "developed", "created", "designed", "built",
        "managed", "led", "directed", "supervised",
    ]

    def score_content(
        self,
        content: str,
        requirement_text: str = None,
        expected_citations: int = None,
    ) -> Dict[str, Any]:
        """
        Score AI-generated content quality.

        Args:
            content: The generated proposal content
            requirement_text: The requirement being addressed
            expected_citations: Expected number of citations

        Returns:
            Quality score breakdown
        """
        scores = {}

        # Citation Analysis
        citation_pattern = r'\[\[Source:\s*[^\]]+\]\]'
        citations = re.findall(citation_pattern, content)
        citation_count = len(citations)

        # Sentences vs citations ratio
        sentences = len(re.findall(r'[.!?]+', content))
        citation_ratio = citation_count / max(sentences, 1)

        if citation_ratio >= 0.3:
            scores["citation_coverage"] = 100
        elif citation_ratio >= 0.2:
            scores["citation_coverage"] = 80
        elif citation_ratio >= 0.1:
            scores["citation_coverage"] = 60
        else:
            scores["citation_coverage"] = 40

        # Check for [NEEDS SOURCE] markers
        needs_source = content.count("[NEEDS SOURCE]")
        if needs_source > 0:
            scores["citation_coverage"] -= needs_source * 10

        # Specificity Analysis
        word_count = len(content.split())

        # Count vague phrases
        vague_count = sum(1 for phrase in self.VAGUE_PHRASES if phrase.lower() in content.lower())
        vague_ratio = vague_count / max(word_count / 100, 1)

        if vague_ratio < 0.5:
            scores["specificity"] = 100
        elif vague_ratio < 1:
            scores["specificity"] = 80
        elif vague_ratio < 2:
            scores["specificity"] = 60
        else:
            scores["specificity"] = 40

        # Check for numbers/metrics (specific is better)
        numbers = len(re.findall(r'\d+(?:\.\d+)?%?', content))
        if numbers >= 5:
            scores["specificity"] = min(100, scores["specificity"] + 20)
        elif numbers >= 3:
            scores["specificity"] = min(100, scores["specificity"] + 10)

        # Writing Quality
        # Check for strong verbs
        strong_verb_count = sum(1 for verb in self.STRONG_VERBS if verb.lower() in content.lower())

        if strong_verb_count >= 5:
            scores["writing_quality"] = 100
        elif strong_verb_count >= 3:
            scores["writing_quality"] = 80
        elif strong_verb_count >= 1:
            scores["writing_quality"] = 60
        else:
            scores["writing_quality"] = 50

        # Check for active voice indicators
        passive_patterns = ["is being", "was being", "has been", "will be", "being"]
        passive_count = sum(1 for p in passive_patterns if p in content.lower())
        if passive_count > 3:
            scores["writing_quality"] -= 10

        # Requirement Coverage (if requirement provided)
        if requirement_text:
            # Extract key terms from requirement
            req_words = set(
                word.lower() for word in requirement_text.split()
                if len(word) > 4 and word.isalpha()
            )

            # Check how many appear in content
            matched = sum(1 for word in req_words if word in content.lower())
            match_ratio = matched / max(len(req_words), 1)

            if match_ratio >= 0.5:
                scores["requirement_coverage"] = 100
            elif match_ratio >= 0.3:
                scores["requirement_coverage"] = 80
            elif match_ratio >= 0.2:
                scores["requirement_coverage"] = 60
            else:
                scores["requirement_coverage"] = 40
        else:
            scores["requirement_coverage"] = 70  # Unknown

        # Length appropriateness
        if word_count < 100:
            scores["length"] = 50  # Too short
        elif word_count < 200:
            scores["length"] = 70
        elif word_count < 600:
            scores["length"] = 100  # Sweet spot
        elif word_count < 1000:
            scores["length"] = 80
        else:
            scores["length"] = 60  # May be too long

        # Calculate overall score
        weights = {
            "citation_coverage": 0.25,
            "specificity": 0.20,
            "writing_quality": 0.20,
            "requirement_coverage": 0.25,
            "length": 0.10,
        }

        overall = sum(scores[k] * weights[k] for k in weights if k in scores)

        # Determine rating
        if overall >= 85:
            rating = "Excellent"
        elif overall >= 70:
            rating = "Good"
        elif overall >= 55:
            rating = "Fair"
        else:
            rating = "Needs Improvement"

        # Generate suggestions
        suggestions = []
        if scores.get("citation_coverage", 0) < 70:
            suggestions.append("Add more source citations to support claims")
        if scores.get("specificity", 0) < 70:
            suggestions.append("Replace vague language with specific metrics and examples")
        if scores.get("writing_quality", 0) < 70:
            suggestions.append("Use more active voice and action verbs")
        if scores.get("requirement_coverage", 0) < 70:
            suggestions.append("Ensure all aspects of the requirement are addressed")
        if needs_source > 0:
            suggestions.append(f"Fill in {needs_source} missing source citations")

        return {
            "overall_score": round(overall, 1),
            "rating": rating,
            "breakdown": scores,
            "suggestions": suggestions,
            "metrics": {
                "word_count": word_count,
                "citation_count": citation_count,
                "needs_source_count": needs_source,
                "vague_phrase_count": vague_count,
            },
        }


# Singleton instances
_compliance_checker: Optional[FARComplianceChecker] = None
_quality_scorer: Optional[AIQualityScorer] = None


def get_compliance_checker() -> FARComplianceChecker:
    """Get or create compliance checker singleton."""
    global _compliance_checker
    if _compliance_checker is None:
        _compliance_checker = FARComplianceChecker()
    return _compliance_checker


def get_quality_scorer() -> AIQualityScorer:
    """Get or create quality scorer singleton."""
    global _quality_scorer
    if _quality_scorer is None:
        _quality_scorer = AIQualityScorer()
    return _quality_scorer
