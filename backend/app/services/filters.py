"""
RFP Sniper - Killer Filter Service
====================================
Uses Gemini 1.5 Flash to quickly qualify/disqualify RFPs.

The "Killer Filter" is a critical cost-optimization feature:
- Uses the CHEAP model (Gemini 1.5 Flash) for rapid screening
- Checks RFP against user's qualification profile
- Filters out opportunities before expensive deep analysis
"""

from dataclasses import dataclass

import google.generativeai as genai
import structlog

from app.config import settings
from app.models.rfp import RFP
from app.models.user import ClearanceLevel, UserProfile

logger = structlog.get_logger(__name__)


@dataclass
class FilterResult:
    """
    Result of the Killer Filter analysis.

    Attributes:
        is_qualified: Whether the user should pursue this RFP
        reason: Human-readable explanation
        confidence: Model confidence in the decision (0-1)
        disqualifying_factors: List of specific issues found
        matching_factors: List of positive matches
    """

    is_qualified: bool
    reason: str
    confidence: float
    disqualifying_factors: list[str]
    matching_factors: list[str]

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "is_qualified": self.is_qualified,
            "reason": self.reason,
            "confidence": self.confidence,
            "disqualifying_factors": self.disqualifying_factors,
            "matching_factors": self.matching_factors,
        }


class KillerFilterService:
    """
    Service for quickly filtering RFPs against user qualifications.

    Uses Gemini 1.5 Flash for cost-effective screening:
    - ~$0.00001875 per 1K input tokens (vs $0.00125 for Pro)
    - Fast response times for bulk processing
    - Sufficient reasoning for yes/no decisions
    """

    # System prompt for the filter
    SYSTEM_PROMPT = """You are an expert government contracting advisor. Your job is to quickly determine if a company should pursue an RFP based on their qualifications.

CRITICAL RULES:
1. If ANY mandatory requirement cannot be met, the company is DISQUALIFIED.
2. Security clearance requirements are non-negotiable.
3. Set-aside requirements (8(a), WOSB, SDVOSB, HUBZone) are non-negotiable.
4. NAICS code mismatches are usually disqualifying unless the company has related experience.

Respond in this exact JSON format:
{
    "is_qualified": true/false,
    "reason": "One sentence summary of the decision",
    "confidence": 0.0-1.0,
    "disqualifying_factors": ["list of issues"],
    "matching_factors": ["list of positives"]
}"""

    def __init__(self, api_key: str | None = None):
        """
        Initialize the Killer Filter service.

        Args:
            api_key: Google Gemini API key. Falls back to settings.
        """
        self.api_key = api_key or settings.gemini_api_key
        self.model_name = settings.gemini_model_flash

        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(
                self.model_name,
                system_instruction=self.SYSTEM_PROMPT,
            )
        else:
            self.model = None
            logger.warning("Gemini API key not configured for Killer Filter")

    def _build_user_profile_text(self, profile: UserProfile) -> str:
        """
        Convert user profile to text for the prompt.

        Args:
            profile: User's qualification profile

        Returns:
            Formatted text description
        """
        lines = ["COMPANY QUALIFICATIONS:"]

        if profile.naics_codes:
            lines.append(f"- NAICS Codes: {', '.join(profile.naics_codes)}")
        else:
            lines.append("- NAICS Codes: Not specified (general)")

        clearance_text = {
            ClearanceLevel.NONE: "None",
            ClearanceLevel.PUBLIC_TRUST: "Public Trust",
            ClearanceLevel.SECRET: "Secret",
            ClearanceLevel.TOP_SECRET: "Top Secret",
            ClearanceLevel.TS_SCI: "TS/SCI",
        }
        lines.append(f"- Security Clearance: {clearance_text.get(profile.clearance_level, 'None')}")

        if profile.set_aside_types:
            lines.append(f"- Set-Aside Eligibility: {', '.join(profile.set_aside_types)}")
        else:
            lines.append("- Set-Aside Eligibility: None (Full and Open only)")

        if profile.preferred_states:
            lines.append(f"- Geographic Preference: {', '.join(profile.preferred_states)}")

        if profile.min_contract_value or profile.max_contract_value:
            min_val = f"${profile.min_contract_value:,}" if profile.min_contract_value else "Any"
            max_val = f"${profile.max_contract_value:,}" if profile.max_contract_value else "Any"
            lines.append(f"- Contract Value Range: {min_val} - {max_val}")

        if profile.include_keywords:
            lines.append(f"- Must Match Keywords: {', '.join(profile.include_keywords)}")

        if profile.exclude_keywords:
            lines.append(f"- Exclude If Contains: {', '.join(profile.exclude_keywords)}")

        return "\n".join(lines)

    def _build_rfp_summary(self, rfp: RFP) -> str:
        """
        Build a concise summary of the RFP for filtering.

        Args:
            rfp: The RFP to summarize

        Returns:
            Formatted RFP summary
        """
        lines = ["RFP DETAILS:"]
        lines.append(f"- Title: {rfp.title}")
        lines.append(f"- Agency: {rfp.agency}")

        if rfp.naics_code:
            lines.append(f"- Required NAICS: {rfp.naics_code}")

        if rfp.set_aside:
            lines.append(f"- Set-Aside Type: {rfp.set_aside}")
        else:
            lines.append("- Set-Aside Type: Full and Open Competition")

        if rfp.place_of_performance:
            lines.append(f"- Place of Performance: {rfp.place_of_performance}")

        if rfp.estimated_value:
            lines.append(f"- Estimated Value: ${rfp.estimated_value:,}")

        if rfp.description:
            # Truncate long descriptions
            desc = (
                rfp.description[:2000] + "..." if len(rfp.description) > 2000 else rfp.description
            )
            lines.append(f"\nDESCRIPTION:\n{desc}")

        return "\n".join(lines)

    async def filter_rfp(
        self,
        rfp: RFP,
        profile: UserProfile,
    ) -> FilterResult:
        """
        Run the Killer Filter on an RFP.

        This is the main entry point for filtering. Uses Gemini 1.5 Flash
        to make a quick qualification decision.

        Args:
            rfp: The RFP to evaluate
            profile: User's qualification profile

        Returns:
            FilterResult with qualification decision and reasoning
        """
        if not self.model:
            logger.error("Gemini model not initialized")
            return FilterResult(
                is_qualified=True,  # Fail open if API not configured
                reason="Unable to filter: Gemini API not configured",
                confidence=0.0,
                disqualifying_factors=[],
                matching_factors=[],
            )

        # Build the prompt
        user_text = self._build_user_profile_text(profile)
        rfp_text = self._build_rfp_summary(rfp)

        prompt = f"""Analyze if this company should pursue this government opportunity.

{user_text}

{rfp_text}

Determine if the company is QUALIFIED to bid on this opportunity. Be strict about mandatory requirements."""

        try:
            logger.info(
                "Running Killer Filter",
                rfp_id=rfp.id,
                rfp_title=rfp.title[:50],
            )

            # Call Gemini 1.5 Flash
            response = await self.model.generate_content_async(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.1,  # Low temp for consistent decisions
                    response_mime_type="application/json",
                ),
            )

            # Parse response
            import json

            result_data = json.loads(response.text)

            return FilterResult(
                is_qualified=result_data.get("is_qualified", True),
                reason=result_data.get("reason", "No reason provided"),
                confidence=result_data.get("confidence", 0.5),
                disqualifying_factors=result_data.get("disqualifying_factors", []),
                matching_factors=result_data.get("matching_factors", []),
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            return FilterResult(
                is_qualified=True,
                reason="Filter parsing error - manual review recommended",
                confidence=0.0,
                disqualifying_factors=[],
                matching_factors=[],
            )
        except Exception as e:
            logger.error(f"Killer Filter error: {e}")
            return FilterResult(
                is_qualified=True,
                reason=f"Filter error: {str(e)}",
                confidence=0.0,
                disqualifying_factors=[],
                matching_factors=[],
            )

    async def batch_filter(
        self,
        rfps: list[RFP],
        profile: UserProfile,
    ) -> list[tuple[RFP, FilterResult]]:
        """
        Filter multiple RFPs in batch.

        Args:
            rfps: List of RFPs to filter
            profile: User's qualification profile

        Returns:
            List of (RFP, FilterResult) tuples
        """
        results = []

        for rfp in rfps:
            result = await self.filter_rfp(rfp, profile)
            results.append((rfp, result))

            logger.info(
                "Filter result",
                rfp_id=rfp.id,
                qualified=result.is_qualified,
                confidence=result.confidence,
            )

        # Summary stats
        qualified_count = sum(1 for _, r in results if r.is_qualified)
        logger.info(
            f"Batch filter complete: {qualified_count}/{len(rfps)} qualified",
        )

        return results


# =============================================================================
# Rule-Based Pre-Filter (No AI, instant disqualification)
# =============================================================================


def quick_disqualify(rfp: RFP, profile: UserProfile) -> str | None:
    """
    Instant disqualification checks without AI.

    These are hard rules that don't need AI interpretation.
    Run this BEFORE the Gemini filter to save API costs.

    Args:
        rfp: The RFP to check
        profile: User's qualification profile

    Returns:
        Disqualification reason, or None if should proceed to AI filter
    """
    # Check NAICS code mismatch
    if rfp.naics_code and profile.naics_codes:
        if rfp.naics_code not in profile.naics_codes:
            # Check for same industry group (first 4 digits)
            rfp_group = rfp.naics_code[:4]
            profile_groups = [code[:4] for code in profile.naics_codes]
            if rfp_group not in profile_groups:
                return f"NAICS code mismatch: RFP requires {rfp.naics_code}"

    # Check set-aside requirements
    if rfp.set_aside and rfp.set_aside.lower() not in ["full and open", "none", ""]:
        set_aside_lower = rfp.set_aside.lower()
        profile_eligibility = [s.lower() for s in profile.set_aside_types]

        # Common set-aside type mappings
        set_aside_keywords = {
            "8(a)": ["8a", "8(a)"],
            "wosb": ["wosb", "women-owned", "woman-owned"],
            "sdvosb": ["sdvosb", "service-disabled", "veteran"],
            "hubzone": ["hubzone"],
            "small business": ["small business", "sb"],
        }

        is_eligible = False
        for eligibility in profile_eligibility:
            for key, keywords in set_aside_keywords.items():
                if any(kw in eligibility for kw in keywords):
                    if any(kw in set_aside_lower for kw in keywords):
                        is_eligible = True
                        break

        if not is_eligible and set_aside_lower not in profile_eligibility:
            return f"Set-aside requirement not met: {rfp.set_aside}"

    # Check contract value range
    if rfp.estimated_value:
        if profile.min_contract_value and rfp.estimated_value < profile.min_contract_value:
            return f"Contract value ${rfp.estimated_value:,} below minimum ${profile.min_contract_value:,}"

        if profile.max_contract_value and rfp.estimated_value > profile.max_contract_value:
            return f"Contract value ${rfp.estimated_value:,} exceeds maximum ${profile.max_contract_value:,}"

    # Check excluded keywords
    if profile.exclude_keywords:
        text_to_check = f"{rfp.title} {rfp.description or ''}".lower()
        for keyword in profile.exclude_keywords:
            if keyword.lower() in text_to_check:
                return f"Contains excluded keyword: {keyword}"

    return None  # Proceed to AI filter
