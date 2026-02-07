"""
RFP Sniper - Contact Extractor Service
=======================================
AI-powered extraction of contacts from RFP text using Gemini.
"""

import json

import structlog

from app.config import settings

logger = structlog.get_logger(__name__)

EXTRACTION_PROMPT = """Extract all person contacts from the following government RFP/solicitation text.
For each contact found, return a JSON object with these fields:
- name: full name
- title: job title or position
- email: email address if present
- phone: phone number if present
- agency: government agency name
- role: their role in the procurement (e.g., Contracting Officer, COR, Program Manager, COTR)

Return ONLY a JSON array of contact objects. If no contacts found, return [].
Do not include any explanation or markdown formatting.

TEXT:
"""


async def extract_contacts_from_text(text: str) -> list[dict]:
    """
    Extract structured contacts from RFP text using Gemini.

    Falls back to mock data if Gemini is unavailable.

    Returns:
        List of dicts with keys: name, title, email, phone, agency, role
    """
    if not text or not text.strip():
        return []

    # Try Gemini extraction
    if settings.gemini_api_key:
        try:
            return await _extract_with_gemini(text)
        except Exception as e:
            logger.warning("gemini_extraction_failed", error=str(e))

    # Fallback to mock when no API key or on failure
    logger.info("using_mock_contact_extraction")
    return _mock_extract(text)


async def _extract_with_gemini(text: str) -> list[dict]:
    """Use Gemini Flash to extract contacts from text."""
    import google.generativeai as genai

    genai.configure(api_key=settings.gemini_api_key)
    model_name = getattr(settings, "gemini_model_flash", "gemini-1.5-flash")
    model = genai.GenerativeModel(model_name)

    # Truncate to avoid token limits
    truncated = text[:30000] if len(text) > 30000 else text
    prompt = EXTRACTION_PROMPT + truncated

    response = await model.generate_content_async(prompt)
    raw = response.text.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()

    contacts = json.loads(raw)
    if not isinstance(contacts, list):
        return []

    return _normalize_contacts(contacts)


def _mock_extract(text: str) -> list[dict]:
    """Simple regex-based mock extraction for development."""
    contacts: list[dict] = []
    text_lower = text.lower()

    # Look for common contracting officer patterns
    if "contracting officer" in text_lower or "contract specialist" in text_lower:
        contacts.append(
            {
                "name": "Contact extracted from document",
                "title": "Contracting Officer",
                "email": None,
                "phone": None,
                "agency": None,
                "role": "Contracting Officer",
            }
        )

    return contacts


def _normalize_contacts(raw_contacts: list[dict]) -> list[dict]:
    """Normalize extracted contacts to consistent schema."""
    normalized: list[dict] = []
    for c in raw_contacts:
        if not isinstance(c, dict):
            continue
        name = c.get("name", "").strip()
        if not name:
            continue
        normalized.append(
            {
                "name": name,
                "title": _str_or_none(c.get("title")),
                "email": _str_or_none(c.get("email")),
                "phone": _str_or_none(c.get("phone")),
                "agency": _str_or_none(c.get("agency")),
                "role": _str_or_none(c.get("role")),
            }
        )
    return normalized


def _str_or_none(val: object | None) -> str | None:
    """Return stripped string or None."""
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None
