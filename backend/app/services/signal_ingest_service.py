"""Market signal ingestion from RSS/Atom feeds."""

import hashlib
from datetime import datetime

import httpx
import structlog

logger = structlog.get_logger(__name__)

# Curated government contracting news feeds
DEFAULT_FEEDS: list[dict] = [
    {"name": "FedScoop", "url": "https://fedscoop.com/feed/", "category": "federal_it"},
    {"name": "DefenseOne", "url": "https://www.defenseone.com/rss/", "category": "defense"},
    {"name": "FCW", "url": "https://fcw.com/rss/", "category": "federal_it"},
    {"name": "NextGov", "url": "https://www.nextgov.com/rss/", "category": "federal_it"},
    {"name": "GovExec", "url": "https://www.govexec.com/rss/", "category": "federal_policy"},
    {"name": "MeriTalk", "url": "https://www.meritalk.com/feed/", "category": "federal_it"},
    {"name": "ExecutiveGov", "url": "https://executivegov.com/feed/", "category": "govcon"},
    {"name": "WashTech", "url": "https://washingtontechnology.com/rss/", "category": "govcon"},
]


class SignalIngestService:
    """Fetches and parses government contracting news from RSS feeds."""

    def __init__(self, feeds: list[dict] | None = None):
        self.feeds = feeds or DEFAULT_FEEDS

    async def fetch_all_feeds(self) -> list[dict]:
        """Fetch all configured RSS feeds and return parsed entries."""
        all_entries: list[dict] = []

        async with httpx.AsyncClient(timeout=15) as client:
            for feed_config in self.feeds:
                try:
                    entries = await self._fetch_feed(client, feed_config)
                    all_entries.extend(entries)
                except Exception as exc:
                    logger.error(
                        "Feed fetch failed",
                        feed=feed_config["name"],
                        error=str(exc),
                    )

        return all_entries

    async def _fetch_feed(self, client: httpx.AsyncClient, feed_config: dict) -> list[dict]:
        """Fetch and parse a single RSS/Atom feed."""
        resp = await client.get(feed_config["url"])
        resp.raise_for_status()
        content = resp.text

        # Simple XML parsing without external dependency
        entries: list[dict] = []
        items = _extract_xml_items(content)

        for item in items:
            entry_id = hashlib.sha256(
                (item.get("link", "") + item.get("title", "")).encode()
            ).hexdigest()[:16]

            entries.append(
                {
                    "external_id": f"signal-{entry_id}",
                    "title": item.get("title", "Untitled"),
                    "description": item.get("description", item.get("summary", "")),
                    "url": item.get("link", ""),
                    "published_date": item.get("pubDate", item.get("published", "")),
                    "source_name": feed_config["name"],
                    "category": feed_config["category"],
                    "fetched_at": datetime.utcnow().isoformat(),
                }
            )

        return entries


def _extract_xml_items(xml_text: str) -> list[dict]:
    """Lightweight XML parser for RSS/Atom items without external deps."""
    import re

    items: list[dict] = []

    # Try RSS <item> tags first, then Atom <entry> tags
    item_pattern = re.compile(r"<item>(.*?)</item>", re.DOTALL)
    if not item_pattern.findall(xml_text):
        item_pattern = re.compile(r"<entry>(.*?)</entry>", re.DOTALL)

    for match in item_pattern.findall(xml_text):
        item: dict = {}
        for tag in ["title", "link", "description", "summary", "pubDate", "published"]:
            tag_match = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", match, re.DOTALL)
            if tag_match:
                value = tag_match.group(1).strip()
                # Strip CDATA wrappers
                value = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", value, flags=re.DOTALL)
                item[tag] = value

        # Handle Atom <link href="..."/> format
        if "link" not in item:
            link_match = re.search(r'<link[^>]*href="([^"]*)"', match)
            if link_match:
                item["link"] = link_match.group(1)

        if item:
            items.append(item)

    return items
