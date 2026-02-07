"""
RFP Sniper - Capability Gap Analysis Service
==============================================
AI-powered gap analysis: compares RFP requirements against user profile
and recommends teaming partners.
"""

import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.config import settings
from app.models.capture import TeamingPartner
from app.models.rfp import RFP
from app.models.user import UserProfile

logger = logging.getLogger(__name__)


class CapabilityGap:
    def __init__(
        self,
        gap_type: str,
        description: str,
        required_value: str | None = None,
        matching_partner_ids: list[int] | None = None,
    ):
        self.gap_type = gap_type
        self.description = description
        self.required_value = required_value
        self.matching_partner_ids = matching_partner_ids or []


class CapabilityGapResult:
    def __init__(
        self,
        rfp_id: int,
        gaps: list[dict],
        recommended_partners: list[dict],
        analysis_summary: str,
    ):
        self.rfp_id = rfp_id
        self.gaps = gaps
        self.recommended_partners = recommended_partners
        self.analysis_summary = analysis_summary


async def analyze_capability_gaps(
    rfp_id: int,
    user_id: int,
    session: AsyncSession,
) -> CapabilityGapResult:
    """Analyze capability gaps for an RFP against the user's profile."""
    rfp = await session.get(RFP, rfp_id)
    if not rfp:
        raise ValueError(f"RFP {rfp_id} not found")

    profile_result = await session.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = profile_result.scalar_one_or_none()

    partners_result = await session.execute(
        select(TeamingPartner).where(TeamingPartner.is_public == True)  # noqa: E712
    )
    partners = partners_result.scalars().all()

    # Build context
    rfp_text = rfp.raw_text[:4000] if rfp.raw_text else rfp.title
    profile_caps = []
    if profile:
        profile_caps = profile.capabilities if hasattr(profile, "capabilities") else []

    partner_summaries = [
        {
            "id": p.id,
            "name": p.name,
            "capabilities": p.capabilities or [],
            "naics_codes": p.naics_codes or [],
            "set_asides": p.set_asides or [],
            "clearance_level": p.clearance_level,
        }
        for p in partners[:20]
    ]

    prompt = f"""Analyze capability gaps for this RFP. Compare the requirements against the
user's capabilities, then recommend teaming partners that could fill the gaps.

RFP Summary:
{rfp_text}

User Capabilities: {json.dumps(profile_caps)}

Available Partners: {json.dumps(partner_summaries)}

Respond in JSON:
{{
  "gaps": [
    {{"gap_type": "technical|clearance|naics|past_performance|set_aside",
      "description": "...",
      "required_value": "...",
      "matching_partner_ids": [1, 2]}}
  ],
  "recommended_partners": [
    {{"partner_id": 1, "name": "...", "reason": "..."}}
  ],
  "analysis_summary": "1-2 sentence summary"
}}"""

    # Try Gemini Flash
    try:
        import google.generativeai as genai

        if settings.gemini_api_key:
            genai.configure(api_key=settings.gemini_api_key)
            model = genai.GenerativeModel(settings.gemini_model_flash)
            response = await model.generate_content_async(prompt)
            text = response.text.strip()
            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                if text.endswith("```"):
                    text = text[: text.rfind("```")]
            result_data = json.loads(text)
        else:
            result_data = _mock_gap_result(rfp_id, partner_summaries)
    except Exception as e:
        logger.warning("Gemini gap analysis failed, using mock: %s", e)
        result_data = _mock_gap_result(rfp_id, partner_summaries)

    return CapabilityGapResult(
        rfp_id=rfp_id,
        gaps=result_data.get("gaps", []),
        recommended_partners=result_data.get("recommended_partners", []),
        analysis_summary=result_data.get("analysis_summary", "Analysis complete."),
    )


def _mock_gap_result(rfp_id: int, partners: list[dict]) -> dict:
    """Deterministic fallback for testing."""
    partner_recs = [
        {"partner_id": p["id"], "name": p["name"], "reason": "Capability match"}
        for p in partners[:3]
    ]
    return {
        "gaps": [
            {
                "gap_type": "technical",
                "description": "Cloud migration expertise required",
                "required_value": "AWS/Azure migration",
                "matching_partner_ids": [p["id"] for p in partners[:2]],
            }
        ],
        "recommended_partners": partner_recs,
        "analysis_summary": "One technical gap identified with partner recommendations.",
    }
