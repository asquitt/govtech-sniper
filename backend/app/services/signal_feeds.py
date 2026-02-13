"""
Market signal feed service — RSS polling and relevance scoring.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import feedparser
import structlog

from app.models.market_signal import SignalType

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# RSS Feed Registry — government procurement news/award/budget feeds
# ---------------------------------------------------------------------------
RSS_FEED_REGISTRY: list[dict[str, str]] = [
    {
        "name": "SAM.gov Recent Opportunities",
        "url": "https://sam.gov/api/prod/opps/v1/rss",
        "signal_type": SignalType.NEWS,
    },
    {
        "name": "USAspending Awards",
        "url": "https://www.usaspending.gov/api/v2/awards/feed/",
        "signal_type": SignalType.AWARD,
    },
    {
        "name": "Congressional Budget Office Reports",
        "url": "https://www.cbo.gov/publications/feed",
        "signal_type": SignalType.BUDGET,
    },
    {
        "name": "GovWin Procurement News",
        "url": "https://iq.govwin.com/neo/feeds/recent-opportunities",
        "signal_type": SignalType.NEWS,
    },
]


def fetch_feed(feed_config: dict[str, str]) -> list[dict[str, Any]]:
    """Parse an RSS feed and return structured entries."""
    url = feed_config["url"]
    signal_type = feed_config.get("signal_type", SignalType.NEWS)

    try:
        parsed = feedparser.parse(url)
    except Exception as exc:
        logger.error("Feed parse error", url=url, error=str(exc))
        return []

    entries: list[dict[str, Any]] = []
    for entry in parsed.entries[:50]:  # Cap at 50 per feed
        published = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                published = datetime(*entry.published_parsed[:6])
            except (TypeError, ValueError):
                pass

        entries.append(
            {
                "title": getattr(entry, "title", "")[:255],
                "content": getattr(entry, "summary", "")[:2000],
                "source_url": getattr(entry, "link", "")[:500],
                "signal_type": signal_type,
                "agency": _extract_agency_from_entry(entry),
                "published_at": published,
            }
        )

    return entries


def score_relevance(
    entry: dict[str, Any],
    agencies: list[str],
    naics_codes: list[str],
    keywords: list[str],
) -> float:
    """Score an entry against a user's subscription preferences.

    Returns 0.0–1.0 relevance score.
    """
    score = 0.0
    combined = f"{entry.get('title', '')} {entry.get('content', '')}".lower()
    entry_agency = (entry.get("agency") or "").lower()

    # Agency match (high signal)
    for agency in agencies:
        if agency.lower() in combined or agency.lower() == entry_agency:
            score += 0.4
            break

    # Keyword match
    kw_hits = sum(1 for kw in keywords if kw.lower() in combined)
    if keywords:
        score += min(0.4, kw_hits * 0.15)

    # NAICS match
    for code in naics_codes:
        if code in combined:
            score += 0.2
            break

    return min(1.0, score)


def _extract_agency_from_entry(entry: Any) -> str | None:
    """Try to extract an agency name from a feed entry."""
    title = getattr(entry, "title", "")
    # Many gov feeds include agency in title or author
    author = getattr(entry, "author", "")
    for field in [author, title]:
        for suffix in (".gov", "Department of", "Agency", "Administration"):
            if suffix.lower() in field.lower():
                return field[:100]
    return None
