"""
RFP Sniper - Bid Decision Service
===================================
AI-powered bid/no-bid evaluation using weighted criteria scoring.
Uses Gemini Pro for deep analysis of opportunity fit.
"""

import json

import google.generativeai as genai
import structlog

from app.config import settings
from app.models.capture import BidScorecard, BidScorecardRecommendation, ScorerType
from app.models.rfp import RFP
from app.models.user import UserProfile

logger = structlog.get_logger(__name__)

# 12 weighted criteria summing to 100
DEFAULT_BID_CRITERIA = [
    {
        "name": "technical_capability",
        "weight": 15,
        "description": "Ability to deliver the technical requirements",
    },
    {
        "name": "past_performance",
        "weight": 12,
        "description": "Relevant past performance and contract history",
    },
    {"name": "price_competitiveness", "weight": 10, "description": "Ability to compete on price"},
    {
        "name": "staffing_availability",
        "weight": 10,
        "description": "Key personnel and staffing readiness",
    },
    {
        "name": "clearance_requirements",
        "weight": 10,
        "description": "Security clearance compliance",
    },
    {
        "name": "set_aside_eligibility",
        "weight": 8,
        "description": "Set-aside and socioeconomic eligibility",
    },
    {
        "name": "relationship_with_agency",
        "weight": 8,
        "description": "Existing relationship with the agency",
    },
    {
        "name": "competitive_landscape",
        "weight": 7,
        "description": "Competitive positioning and incumbency",
    },
    {"name": "geographic_fit", "weight": 5, "description": "Proximity to place of performance"},
    {
        "name": "contract_vehicle_access",
        "weight": 5,
        "description": "Access to required contract vehicles",
    },
    {
        "name": "teaming_strength",
        "weight": 5,
        "description": "Quality and relevance of teaming arrangements",
    },
    {
        "name": "proposal_timeline",
        "weight": 5,
        "description": "Feasibility of meeting proposal deadline",
    },
]

SYSTEM_PROMPT = """You are a senior government contracting capture manager conducting a bid/no-bid analysis.

Evaluate the opportunity against the company profile using the provided weighted criteria.
For each criterion, provide:
- score: 0-100
- reasoning: 1-2 sentence justification

Then provide an overall recommendation: "bid", "no_bid", or "conditional".

Respond in this exact JSON format:
{
    "criteria_scores": [
        {"name": "criterion_name", "weight": 15, "score": 75, "reasoning": "..."},
        ...
    ],
    "overall_score": 0-100,
    "recommendation": "bid" | "no_bid" | "conditional",
    "confidence": 0.0-1.0,
    "reasoning": "2-3 sentence summary of the bid decision rationale",
    "win_probability": 0-100
}"""


class BidDecisionService:
    """Evaluate opportunities for bid/no-bid decisions using Gemini Pro."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.gemini_api_key
        self.model_name = settings.gemini_model_pro

        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(
                self.model_name,
                system_instruction=SYSTEM_PROMPT,
            )
        else:
            self.model = None
            logger.warning("Gemini API key not configured for bid decision service")

    def _build_prompt(
        self,
        rfp: RFP,
        profile: UserProfile,
        criteria: list[dict],
    ) -> str:
        lines = ["OPPORTUNITY:"]
        lines.append(f"Title: {rfp.title}")
        lines.append(f"Agency: {rfp.agency}")
        if rfp.naics_code:
            lines.append(f"NAICS: {rfp.naics_code}")
        if rfp.set_aside:
            lines.append(f"Set-Aside: {rfp.set_aside}")
        if rfp.estimated_value:
            lines.append(f"Est. Value: ${rfp.estimated_value:,}")
        if rfp.place_of_performance:
            lines.append(f"Location: {rfp.place_of_performance}")
        if rfp.response_deadline:
            lines.append(f"Deadline: {rfp.response_deadline.strftime('%Y-%m-%d')}")
        if rfp.description:
            desc = rfp.description[:3000]
            lines.append(f"\nDescription:\n{desc}")

        lines.append("\n\nCOMPANY PROFILE:")
        if profile.naics_codes:
            lines.append(f"NAICS Codes: {', '.join(profile.naics_codes)}")
        lines.append(f"Clearance: {profile.clearance_level.value}")
        if profile.set_aside_types:
            lines.append(f"Set-Asides: {', '.join(profile.set_aside_types)}")
        if profile.core_competencies:
            lines.append(f"Core Competencies: {', '.join(profile.core_competencies)}")
        if profile.certifications:
            lines.append(f"Certifications: {', '.join(profile.certifications)}")
        if profile.past_performance_summary:
            lines.append(f"Past Performance: {profile.past_performance_summary[:500]}")
        if profile.years_in_business:
            lines.append(f"Years in Business: {profile.years_in_business}")
        if profile.employee_count:
            lines.append(f"Employees: {profile.employee_count}")

        lines.append("\n\nEVALUATION CRITERIA:")
        for c in criteria:
            lines.append(f"- {c['name']} (weight: {c['weight']}): {c['description']}")

        lines.append("\n\nEvaluate each criterion and provide your bid/no-bid recommendation.")
        return "\n".join(lines)

    async def evaluate(
        self,
        rfp: RFP,
        profile: UserProfile,
        user_id: int,
        criteria: list[dict] | None = None,
    ) -> BidScorecard:
        """Run AI bid/no-bid evaluation. Returns a BidScorecard ready to persist."""
        criteria = criteria or DEFAULT_BID_CRITERIA

        if not self.model:
            return BidScorecard(
                rfp_id=rfp.id,
                user_id=user_id,
                criteria_scores=[],
                overall_score=0.0,
                recommendation=None,
                confidence=0.0,
                reasoning="Gemini API not configured",
                scorer_type=ScorerType.AI,
            )

        prompt = self._build_prompt(rfp, profile, criteria)

        try:
            response = await self.model.generate_content_async(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.2,
                    response_mime_type="application/json",
                ),
            )
            data = json.loads(response.text)

            rec_str = data.get("recommendation", "conditional")
            recommendation = BidScorecardRecommendation(rec_str)

            scorecard = BidScorecard(
                rfp_id=rfp.id,
                user_id=user_id,
                criteria_scores=data.get("criteria_scores", []),
                overall_score=float(data.get("overall_score", 0)),
                recommendation=recommendation,
                confidence=float(data.get("confidence", 0.5)),
                reasoning=data.get("reasoning", ""),
                scorer_type=ScorerType.AI,
            )

            return scorecard

        except json.JSONDecodeError as e:
            logger.error("Failed to parse bid decision response", error=str(e))
            return BidScorecard(
                rfp_id=rfp.id,
                user_id=user_id,
                criteria_scores=[],
                overall_score=0.0,
                recommendation=None,
                confidence=0.0,
                reasoning=f"Response parse error: {e}",
                scorer_type=ScorerType.AI,
            )
        except Exception as e:
            logger.error("Bid decision service error", error=str(e))
            return BidScorecard(
                rfp_id=rfp.id,
                user_id=user_id,
                criteria_scores=[],
                overall_score=0.0,
                recommendation=None,
                confidence=0.0,
                reasoning=str(e),
                scorer_type=ScorerType.AI,
            )

    @staticmethod
    def compute_win_probability(scorecard: BidScorecard) -> int:
        """Derive win probability from scorecard scores."""
        if not scorecard.criteria_scores:
            return 0

        total_weighted = 0.0
        total_weight = 0.0
        for cs in scorecard.criteria_scores:
            weight = cs.get("weight", 1)
            score = cs.get("score", 0)
            total_weighted += weight * score
            total_weight += weight

        if total_weight == 0:
            return 0

        return int(total_weighted / total_weight)
