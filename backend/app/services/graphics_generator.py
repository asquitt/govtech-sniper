"""
RFP Sniper - AI Graphics Generator
====================================
Uses Gemini to generate SVG/Mermaid diagrams from proposal content.
"""

import logging

from app.config import settings

logger = logging.getLogger(__name__)

TEMPLATE_TYPES = [
    "management_approach",
    "staffing_plan",
    "timeline",
    "org_chart",
    "process_flow",
]

TEMPLATE_PROMPTS = {
    "management_approach": (
        "Create a Mermaid flowchart that illustrates the management approach "
        "described below. Show key roles, reporting lines, and decision flows. "
        "Use clear labels. Output ONLY the Mermaid diagram code."
    ),
    "staffing_plan": (
        "Create a Mermaid Gantt chart showing the staffing timeline based on "
        "the description below. Show phases, key personnel onboarding, and "
        "ramp-up periods. Output ONLY the Mermaid diagram code."
    ),
    "timeline": (
        "Create a Mermaid Gantt chart showing the project timeline described "
        "below. Include major milestones, phases, and deliverable dates. "
        "Output ONLY the Mermaid diagram code."
    ),
    "org_chart": (
        "Create a Mermaid flowchart (top-down) showing the organizational "
        "structure described below. Include all roles, reporting relationships, "
        "and any matrix connections. Output ONLY the Mermaid diagram code."
    ),
    "process_flow": (
        "Create a Mermaid flowchart showing the process flow described below. "
        "Include decision points, parallel activities, and key outputs. "
        "Output ONLY the Mermaid diagram code."
    ),
}


async def generate_graphic(
    content: str,
    template_type: str,
    title: str | None = None,
) -> dict:
    """
    Generate a Mermaid diagram from proposal content using Gemini.

    Returns:
        dict with keys: mermaid_code, template_type, title
    """
    if template_type not in TEMPLATE_PROMPTS:
        raise ValueError(f"Unknown template type: {template_type}")

    system_prompt = TEMPLATE_PROMPTS[template_type]
    user_prompt = f"Title: {title or 'Untitled'}\n\nContent:\n{content[:4000]}"

    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            [
                {"role": "user", "parts": [f"{system_prompt}\n\n{user_prompt}"]},
            ],
            generation_config={"temperature": 0.3, "max_output_tokens": 2000},
        )

        mermaid_code = response.text.strip()
        # Strip markdown code fences if present
        if mermaid_code.startswith("```"):
            lines = mermaid_code.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            mermaid_code = "\n".join(lines).strip()

        return {
            "mermaid_code": mermaid_code,
            "template_type": template_type,
            "title": title or "Generated Graphic",
        }

    except ImportError:
        logger.warning("google-generativeai not installed, returning placeholder")
        return {
            "mermaid_code": _placeholder_mermaid(template_type, title),
            "template_type": template_type,
            "title": title or "Generated Graphic",
        }
    except Exception as e:
        logger.error(f"Gemini graphics generation failed: {e}")
        return {
            "mermaid_code": _placeholder_mermaid(template_type, title),
            "template_type": template_type,
            "title": title or "Generated Graphic",
            "error": str(e),
        }


def _placeholder_mermaid(template_type: str, title: str | None) -> str:
    """Placeholder Mermaid code when Gemini is unavailable."""
    label = title or template_type.replace("_", " ").title()
    if template_type in ("timeline", "staffing_plan"):
        return f"""gantt
    title {label}
    dateFormat  YYYY-MM-DD
    section Phase 1
    Planning :a1, 2025-01-01, 30d
    section Phase 2
    Execution :a2, after a1, 60d
    section Phase 3
    Delivery :a3, after a2, 30d"""
    return f"""flowchart TD
    A[{label}] --> B[Step 1]
    B --> C[Step 2]
    C --> D[Step 3]
    D --> E[Complete]"""
