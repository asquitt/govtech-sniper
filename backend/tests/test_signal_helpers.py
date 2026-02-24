"""
Signal Route Helper Unit Tests
================================
Tests for pure helper functions in signals.py route module.
"""

from datetime import datetime
from unittest.mock import MagicMock

from app.api.routes.signals import (
    _fallback_news,
    _normalize_text,
    _parse_rss_date,
    _score_signal,
)
from app.models.market_signal import SignalType

# =============================================================================
# _normalize_text
# =============================================================================


class TestNormalizeText:
    def test_basic(self):
        assert _normalize_text("  Hello World  ") == "hello world"

    def test_none(self):
        assert _normalize_text(None) == ""

    def test_empty(self):
        assert _normalize_text("") == ""


# =============================================================================
# _parse_rss_date
# =============================================================================


class TestParseRSSDate:
    def test_valid_rfc2822(self):
        result = _parse_rss_date("Mon, 24 Feb 2026 10:00:00 GMT")
        assert isinstance(result, datetime)

    def test_none(self):
        assert _parse_rss_date(None) is None

    def test_empty(self):
        assert _parse_rss_date("") is None

    def test_invalid(self):
        assert _parse_rss_date("not-a-date") is None


# =============================================================================
# _fallback_news
# =============================================================================


class TestFallbackNews:
    def test_returns_two_entries(self):
        now = datetime(2026, 2, 24)
        news = _fallback_news(now)
        assert len(news) == 2

    def test_includes_month_label(self):
        now = datetime(2026, 2, 24)
        news = _fallback_news(now)
        assert "February 2026" in news[0]["title"]

    def test_has_required_fields(self):
        now = datetime(2026, 2, 24)
        for item in _fallback_news(now):
            assert "title" in item
            assert "agency" in item
            assert "content" in item
            assert "source_url" in item
            assert "published_at" in item


# =============================================================================
# _score_signal
# =============================================================================


def _mock_subscription(**kwargs):
    sub = MagicMock()
    sub.agencies = kwargs.get("agencies", [])
    sub.keywords = kwargs.get("keywords", [])
    sub.naics_codes = kwargs.get("naics_codes", [])
    return sub


class TestScoreSignal:
    def test_no_subscription_baseline(self):
        score = _score_signal("Test Title", None, None, SignalType.NEWS, None)
        assert score == 15.0

    def test_budget_type_bonus(self):
        score = _score_signal("Budget Update", None, None, SignalType.BUDGET, None)
        assert score == 23.0  # 15 + 8

    def test_recompete_type_bonus(self):
        score = _score_signal("Recompete", None, None, SignalType.RECOMPETE, None)
        assert score == 21.0  # 15 + 6

    def test_agency_match(self):
        sub = _mock_subscription(agencies=["Department of Defense"])
        score = _score_signal(
            "DoD Cloud Services", "Department of Defense procurement", "DoD", SignalType.NEWS, sub
        )
        assert score > 15.0

    def test_keyword_match(self):
        sub = _mock_subscription(keywords=["cybersecurity", "cloud"])
        score = _score_signal(
            "Cybersecurity cloud migration",
            "Moving to cloud infrastructure",
            None,
            SignalType.NEWS,
            sub,
        )
        assert score > 15.0

    def test_naics_match(self):
        sub = _mock_subscription(naics_codes=["541512"])
        score = _score_signal("IT Services 541512", None, None, SignalType.NEWS, sub)
        assert score > 15.0

    def test_score_capped_at_100(self):
        sub = _mock_subscription(
            agencies=["DoD"],
            keywords=["cyber", "cloud", "AI", "ML"],
            naics_codes=["541512"],
        )
        score = _score_signal(
            "DoD cyber cloud AI ML 541512",
            "DoD cyber cloud AI ML 541512",
            "DoD",
            SignalType.BUDGET,
            sub,
        )
        assert score <= 100.0

    def test_empty_subscription_fields(self):
        sub = _mock_subscription(agencies=[], keywords=[], naics_codes=[])
        score = _score_signal("Generic Title", None, None, SignalType.NEWS, sub)
        assert score == 15.0
