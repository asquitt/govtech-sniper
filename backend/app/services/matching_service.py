"""
RFP Sniper - Opportunity Matching Service
==========================================
AI-powered scoring of opportunities against user company profiles.
Uses Gemini Flash for cost-effective multi-category scoring.
"""

import json
from dataclasses import dataclass, field

import google.generativeai as genai
import structlog

from app.config import settings
from app.models.rfp import RFP
from app.models.user import UserProfile

logger = structlog.get_logger(__name__)

SCORING_CATEGORIES = [
    "naics_fit",
    "set_aside_eligibility",
    "clearance_match",
    "past_performance_relevance",
    "contract_value_fit",
    "geographic_alignment",
    "core_competency_match",
    "certification_requirements",
]

SYSTEM_PROMPT = """You are an expert government contracting opportunity analyst.
Score how well an opportunity matches a company's profile across 8 categories.

For each category, provide a score from 0-100:
- naics_fit: How well the NAICS code matches the company's codes
- set_aside_eligibility: Whether the company meets set-aside requirements
- clearance_match: Whether the company meets security clearance requirements
- past_performance_relevance: How relevant the company's past performance is
- contract_value_fit: Whether the contract value is in the company's range
- geographic_alignment: Whether the location matches company preferences
- core_competency_match: How well the work aligns with company strengths
- certification_requirements: Whether the company holds needed certifications

Respond in this exact JSON format:
{
    "overall_score": 0-100,
    "category_scores": {
        "naics_fit": 0-100,
        "set_aside_eligibility": 0-100,
        "clearance_match": 0-100,
        "past_performance_relevance": 0-100,
        "contract_value_fit": 0-100,
        "geographic_alignment": 0-100,
        "core_competency_match": 0-100,
        "certification_requirements": 0-100
    },
    "strengths": ["list of top matching factors"],
    "gaps": ["list of gaps or risks"],
    "reasoning": "2-3 sentence summary of the match quality"
}"""


@dataclass
class MatchResult:
    overall_score: float
    category_scores: dict[str, float]
    strengths: list[str]
    gaps: list[str]
    reasoning: str

    def to_dict(self) -> dict:
        return {
            "overall_score": self.overall_score,
            "category_scores": self.category_scores,
            "strengths": self.strengths,
            "gaps": self.gaps,
            "reasoning": self.reasoning,
        }


@dataclass
class BatchMatchResult:
    results: list[tuple[int, MatchResult]] = field(default_factory=list)
    errors: list[tuple[int, str]] = field(default_factory=list)


class OpportunityMatchingService:
    """Score opportunities against user profiles using Gemini Flash."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.gemini_api_key
        self.model_name = settings.gemini_model_flash

        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(
                self.model_name,
                system_instruction=SYSTEM_PROMPT,
            )
        else:
            self.model = None
            logger.warning("Gemini API key not configured for matching service")

    def _build_profile_text(self, profile: UserProfile) -> str:
        lines = ["COMPANY PROFILE:"]
        if profile.naics_codes:
            lines.append(f"- NAICS Codes: {', '.join(profile.naics_codes)}")
        lines.append(f"- Clearance: {profile.clearance_level.value}")
        if profile.set_aside_types:
            lines.append(f"- Set-Aside Eligibility: {', '.join(profile.set_aside_types)}")
        if profile.preferred_states:
            lines.append(f"- Geographic Preference: {', '.join(profile.preferred_states)}")
        if profile.min_contract_value or profile.max_contract_value:
            min_v = f"${profile.min_contract_value:,}" if profile.min_contract_value else "Any"
            max_v = f"${profile.max_contract_value:,}" if profile.max_contract_value else "Any"
            lines.append(f"- Contract Value Range: {min_v} - {max_v}")
        if profile.core_competencies:
            lines.append(f"- Core Competencies: {', '.join(profile.core_competencies)}")
        if profile.certifications:
            lines.append(f"- Certifications: {', '.join(profile.certifications)}")
        if profile.past_performance_summary:
            summary = profile.past_performance_summary[:500]
            lines.append(f"- Past Performance: {summary}")
        if profile.years_in_business:
            lines.append(f"- Years in Business: {profile.years_in_business}")
        if profile.annual_revenue:
            lines.append(f"- Annual Revenue: ${profile.annual_revenue:,}")
        if profile.employee_count:
            lines.append(f"- Employees: {profile.employee_count}")
        return "\n".join(lines)

    def _build_rfp_text(self, rfp: RFP) -> str:
        lines = ["OPPORTUNITY:"]
        lines.append(f"- Title: {rfp.title}")
        lines.append(f"- Agency: {rfp.agency}")
        if rfp.naics_code:
            lines.append(f"- NAICS: {rfp.naics_code}")
        if rfp.set_aside:
            lines.append(f"- Set-Aside: {rfp.set_aside}")
        if rfp.place_of_performance:
            lines.append(f"- Location: {rfp.place_of_performance}")
        if rfp.estimated_value:
            lines.append(f"- Est. Value: ${rfp.estimated_value:,}")
        if rfp.contract_vehicle:
            lines.append(f"- Vehicle: {rfp.contract_vehicle}")
        if rfp.description:
            desc = (
                rfp.description[:2000] + "..." if len(rfp.description) > 2000 else rfp.description
            )
            lines.append(f"\nDESCRIPTION:\n{desc}")
        return "\n".join(lines)

    async def score_opportunity(self, rfp: RFP, profile: UserProfile) -> MatchResult:
        """Score a single opportunity against the user's profile."""
        if not self.model:
            return MatchResult(
                overall_score=0.0,
                category_scores={c: 0.0 for c in SCORING_CATEGORIES},
                strengths=[],
                gaps=["AI matching not configured"],
                reasoning="Gemini API not configured",
            )

        profile_text = self._build_profile_text(profile)
        rfp_text = self._build_rfp_text(rfp)
        prompt = f"""Score this opportunity match:\n\n{profile_text}\n\n{rfp_text}"""

        try:
            response = await self.model.generate_content_async(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )
            data = json.loads(response.text)
            return MatchResult(
                overall_score=float(data.get("overall_score", 0)),
                category_scores=data.get("category_scores", {}),
                strengths=data.get("strengths", []),
                gaps=data.get("gaps", []),
                reasoning=data.get("reasoning", ""),
            )
        except json.JSONDecodeError as e:
            logger.error("Failed to parse match response", error=str(e))
            return MatchResult(
                overall_score=0.0,
                category_scores={},
                strengths=[],
                gaps=["AI response parsing failed"],
                reasoning=f"Parse error: {e}",
            )
        except Exception as e:
            logger.error("Matching service error", error=str(e))
            return MatchResult(
                overall_score=0.0,
                category_scores={},
                strengths=[],
                gaps=["AI matching error"],
                reasoning=str(e),
            )

    async def batch_score(self, rfps: list[RFP], profile: UserProfile) -> BatchMatchResult:
        """Score multiple opportunities."""
        batch = BatchMatchResult()
        for rfp in rfps:
            try:
                result = await self.score_opportunity(rfp, profile)
                batch.results.append((rfp.id, result))
            except Exception as e:
                batch.errors.append((rfp.id, str(e)))
                logger.error("Batch score error", rfp_id=rfp.id, error=str(e))
        return batch
