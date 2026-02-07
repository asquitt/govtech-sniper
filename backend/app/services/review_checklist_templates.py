"""
RFP Sniper - Review Checklist Templates
========================================
Predefined checklists for Pink, Red, and Gold team reviews.
"""

PINK_TEAM_CHECKLIST: list[dict] = [
    {
        "category": "Story & Themes",
        "item_text": "Win themes are clearly articulated",
        "display_order": 1,
    },
    {
        "category": "Story & Themes",
        "item_text": "Executive summary conveys compelling narrative",
        "display_order": 2,
    },
    {
        "category": "Story & Themes",
        "item_text": "Solution discriminators are highlighted",
        "display_order": 3,
    },
    {
        "category": "Responsiveness",
        "item_text": "All PWS/SOW requirements addressed",
        "display_order": 4,
    },
    {
        "category": "Responsiveness",
        "item_text": "Response maps to evaluation criteria",
        "display_order": 5,
    },
    {
        "category": "Responsiveness",
        "item_text": "Cross-references are accurate",
        "display_order": 6,
    },
    {
        "category": "Content Quality",
        "item_text": "Writing is clear and professional",
        "display_order": 7,
    },
    {
        "category": "Content Quality",
        "item_text": "Graphics support key messages",
        "display_order": 8,
    },
    {
        "category": "Content Quality",
        "item_text": "Past performance citations are relevant",
        "display_order": 9,
    },
]

RED_TEAM_CHECKLIST: list[dict] = [
    {
        "category": "Compliance",
        "item_text": "All Section L instructions followed",
        "display_order": 1,
    },
    {"category": "Compliance", "item_text": "All Section M criteria addressed", "display_order": 2},
    {"category": "Compliance", "item_text": "Page limits met for all volumes", "display_order": 3},
    {
        "category": "Compliance",
        "item_text": "Required certifications/representations included",
        "display_order": 4,
    },
    {
        "category": "Format",
        "item_text": "Font, margins, spacing per RFP requirements",
        "display_order": 5,
    },
    {
        "category": "Format",
        "item_text": "Section numbering matches RFP structure",
        "display_order": 6,
    },
    {"category": "Format", "item_text": "Table of contents is accurate", "display_order": 7},
    {
        "category": "Evaluation Criteria",
        "item_text": "Technical approach scored against evaluation factors",
        "display_order": 8,
    },
    {
        "category": "Evaluation Criteria",
        "item_text": "Management approach addresses all subfactors",
        "display_order": 9,
    },
    {
        "category": "Evaluation Criteria",
        "item_text": "Past performance examples match contract scope",
        "display_order": 10,
    },
    {
        "category": "Evaluation Criteria",
        "item_text": "Price proposal consistent with technical approach",
        "display_order": 11,
    },
]

GOLD_TEAM_CHECKLIST: list[dict] = [
    {
        "category": "Win Strategy",
        "item_text": "Proposal clearly differentiates from competitors",
        "display_order": 1,
    },
    {
        "category": "Win Strategy",
        "item_text": "Price-to-win analysis supports competitiveness",
        "display_order": 2,
    },
    {
        "category": "Win Strategy",
        "item_text": "Customer hot buttons addressed throughout",
        "display_order": 3,
    },
    {
        "category": "Risk Assessment",
        "item_text": "Technical risks identified and mitigated",
        "display_order": 4,
    },
    {
        "category": "Risk Assessment",
        "item_text": "Staffing plan is realistic and achievable",
        "display_order": 5,
    },
    {
        "category": "Risk Assessment",
        "item_text": "Schedule is credible with margin",
        "display_order": 6,
    },
    {
        "category": "Go/No-Go",
        "item_text": "Probability of win justifies bid cost",
        "display_order": 7,
    },
    {
        "category": "Go/No-Go",
        "item_text": "Resources are available for proposal effort",
        "display_order": 8,
    },
    {
        "category": "Go/No-Go",
        "item_text": "Strategic alignment with company growth plan",
        "display_order": 9,
    },
]

_TEMPLATES: dict[str, list[dict]] = {
    "pink": PINK_TEAM_CHECKLIST,
    "red": RED_TEAM_CHECKLIST,
    "gold": GOLD_TEAM_CHECKLIST,
}


def get_checklist_template(review_type: str) -> list[dict]:
    """Return the checklist template for the given review type."""
    return _TEMPLATES.get(review_type, [])
