"""
RFP Routes - Shared Helpers
============================
Constants and utility functions for RFP route handlers.
"""

import re

_TOKEN_RE = re.compile(r"[a-z0-9]{3,}")

_AMENDMENT_IMPACT_PROFILES: dict[str, dict[str, str | list[str]]] = {
    "response_deadline": {
        "impact_area": "timeline",
        "severity": "high",
        "actions": [
            "Update schedule, staffing ramp, and delivery dates impacted by the new deadline.",
            "Re-validate review calendar and approval gates against the updated amendment timeline.",
        ],
    },
    "posted_date": {
        "impact_area": "timeline",
        "severity": "medium",
        "actions": [
            "Reconfirm pursuit timeline assumptions tied to amendment publication timing.",
        ],
    },
    "naics_code": {
        "impact_area": "eligibility",
        "severity": "high",
        "actions": [
            "Re-check NAICS alignment and update qualification assertions where referenced.",
            "Validate teaming/vehicle assumptions still satisfy revised NAICS posture.",
        ],
    },
    "set_aside": {
        "impact_area": "eligibility",
        "severity": "high",
        "actions": [
            "Re-validate set-aside eligibility claims and subcontracting strategy references.",
            "Update compliance matrix entries for socioeconomic requirements.",
        ],
    },
    "rfp_type": {
        "impact_area": "eligibility",
        "severity": "medium",
        "actions": [
            "Adjust proposal framing and compliance rationale to match solicitation type changes.",
        ],
    },
    "resource_links_count": {
        "impact_area": "attachments",
        "severity": "medium",
        "actions": [
            "Review newly added attachments and map them to affected sections and requirements.",
        ],
    },
    "resource_links_hash": {
        "impact_area": "attachments",
        "severity": "medium",
        "actions": [
            "Review attachment deltas and trace source updates into section evidence links.",
        ],
    },
    "description_hash": {
        "impact_area": "scope",
        "severity": "high",
        "actions": [
            "Reconcile technical narrative with amended scope language before next review cycle.",
        ],
    },
    "description_length": {
        "impact_area": "scope",
        "severity": "medium",
        "actions": [
            "Re-read amended narrative and update sections where requirement interpretation changed.",
        ],
    },
}


def _as_text(value: object | None) -> str:
    if value is None:
        return ""
    return str(value)


def _tokenize(value: str) -> set[str]:
    return set(_TOKEN_RE.findall(value.lower()))


def _impact_profile(field: str) -> tuple[str, str, list[str]]:
    profile = _AMENDMENT_IMPACT_PROFILES.get(field)
    if not profile:
        return (
            "scope",
            "low",
            [
                "Review this section for amendment alignment and update discriminator language as needed."
            ],
        )
    return (
        str(profile["impact_area"]),
        str(profile["severity"]),
        list(profile["actions"]),  # type: ignore[arg-type]
    )


def _impact_level(score: float) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"
