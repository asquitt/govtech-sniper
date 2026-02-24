"""
Signal Feeds Unit Tests
========================
Tests for score_relevance() — pure scoring, no HTTP calls.
"""

import sys
from types import ModuleType
from unittest.mock import MagicMock

# feedparser may not be installed locally — stub it before importing signal_feeds
if "feedparser" not in sys.modules:
    sys.modules["feedparser"] = MagicMock(spec=ModuleType)

from app.services.signal_feeds import RSS_FEED_REGISTRY, score_relevance


class TestScoreRelevance:
    def test_perfect_match(self):
        entry = {
            "title": "DoD Cybersecurity Contract Awarded",
            "content": "NAICS 541512 cybersecurity services for Department of Defense",
            "agency": "Department of Defense",
        }
        score = score_relevance(
            entry,
            agencies=["Department of Defense"],
            naics_codes=["541512"],
            keywords=["cybersecurity"],
        )
        assert score >= 0.7

    def test_agency_match_only(self):
        entry = {
            "title": "General Services Administration Update",
            "content": "New procurement vehicle released",
            "agency": "GSA",
        }
        score = score_relevance(entry, agencies=["GSA"], naics_codes=[], keywords=[])
        assert 0.3 <= score <= 0.5

    def test_keyword_match_only(self):
        entry = {
            "title": "Cloud migration project announced",
            "content": "New cloud services opportunity",
            "agency": None,
        }
        score = score_relevance(entry, agencies=[], naics_codes=[], keywords=["cloud", "migration"])
        assert score > 0.0
        assert score <= 0.4

    def test_naics_match_only(self):
        entry = {
            "title": "IT services procurement",
            "content": "NAICS code 541512 applicable",
            "agency": None,
        }
        score = score_relevance(entry, agencies=[], naics_codes=["541512"], keywords=[])
        assert 0.15 <= score <= 0.25

    def test_no_match(self):
        entry = {
            "title": "Unrelated news article",
            "content": "Nothing about government contracting",
            "agency": None,
        }
        score = score_relevance(
            entry,
            agencies=["DoD"],
            naics_codes=["541512"],
            keywords=["cybersecurity"],
        )
        assert score == 0.0

    def test_score_capped_at_one(self):
        entry = {
            "title": "DoD cybersecurity cloud AI 541512 machine learning analytics",
            "content": "DoD Department of Defense cybersecurity 541512 cloud AI ML analytics data",
            "agency": "Department of Defense",
        }
        score = score_relevance(
            entry,
            agencies=["Department of Defense"],
            naics_codes=["541512"],
            keywords=["cybersecurity", "cloud", "AI", "machine learning", "analytics", "data"],
        )
        assert score <= 1.0

    def test_case_insensitive_agency(self):
        entry = {
            "title": "department of defense update",
            "content": "",
            "agency": "department of defense",
        }
        score = score_relevance(
            entry, agencies=["Department of Defense"], naics_codes=[], keywords=[]
        )
        assert score >= 0.3

    def test_empty_preferences(self):
        entry = {"title": "Some article", "content": "Content here", "agency": None}
        score = score_relevance(entry, agencies=[], naics_codes=[], keywords=[])
        assert score == 0.0


class TestRSSFeedRegistry:
    def test_has_entries(self):
        assert len(RSS_FEED_REGISTRY) > 0

    def test_entry_structure(self):
        for feed in RSS_FEED_REGISTRY:
            assert "name" in feed
            assert "url" in feed
            assert "signal_type" in feed
