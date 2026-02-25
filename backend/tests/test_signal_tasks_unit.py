"""
Unit tests for signal_tasks Celery tasks.
Tests poll_signal_feeds and send_signal_digest.
"""

import pytest

try:
    from app.tasks.signal_tasks import poll_signal_feeds, send_signal_digest  # noqa: F401

    HAS_FEEDPARSER = True
except (ImportError, ModuleNotFoundError):
    HAS_FEEDPARSER = False

pytestmark = pytest.mark.skipif(not HAS_FEEDPARSER, reason="feedparser not installed")

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch


def _mock_session_ctx(mock_session):
    @asynccontextmanager
    async def _ctx():
        yield mock_session

    return _ctx


@pytest.mark.skipif(not HAS_FEEDPARSER, reason="feedparser not installed")
class TestPollSignalFeeds:
    def test_no_subscriptions_returns_early(self):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        with patch(
            "app.tasks.signal_tasks.get_celery_session_context",
            _mock_session_ctx(mock_session),
        ):
            from app.tasks.signal_tasks import poll_signal_feeds

            result = poll_signal_feeds()
            assert result["status"] == "ok"
            assert result["created"] == 0
            assert result["feeds_polled"] == 0

    def test_creates_signals_from_feeds(self):
        mock_sub = MagicMock()
        mock_sub.user_id = 1
        mock_sub.agencies = ["DoD"]
        mock_sub.naics_codes = ["541512"]
        mock_sub.keywords = ["cybersecurity"]

        mock_session = AsyncMock()
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalars.return_value.all.return_value = [mock_sub]
            else:
                result.scalar_one_or_none.return_value = None
            return result

        mock_session.execute = AsyncMock(side_effect=side_effect)

        feed_entry = {
            "title": "Test Signal",
            "signal_type": "contract_award",
            "agency": "DoD",
            "content": "Test content",
            "source_url": "https://example.com",
            "published_at": None,
        }

        with (
            patch(
                "app.tasks.signal_tasks.get_celery_session_context",
                _mock_session_ctx(mock_session),
            ),
            patch("app.tasks.signal_tasks.RSS_FEED_REGISTRY", [{"url": "test"}]),
            patch("app.tasks.signal_tasks.fetch_feed", return_value=[feed_entry]),
            patch("app.tasks.signal_tasks.score_relevance", return_value=0.8),
        ):
            from app.tasks.signal_tasks import poll_signal_feeds

            result = poll_signal_feeds()
            assert result["status"] == "ok"
            assert result["feeds_polled"] == 1
            assert result["created"] == 1

    def test_below_threshold_not_created(self):
        mock_sub = MagicMock()
        mock_sub.user_id = 1
        mock_sub.agencies = []
        mock_sub.naics_codes = []
        mock_sub.keywords = []

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_sub]
        mock_session.execute.return_value = mock_result

        feed_entry = {"title": "Irrelevant", "signal_type": "news"}

        with (
            patch(
                "app.tasks.signal_tasks.get_celery_session_context",
                _mock_session_ctx(mock_session),
            ),
            patch("app.tasks.signal_tasks.RSS_FEED_REGISTRY", [{"url": "test"}]),
            patch("app.tasks.signal_tasks.fetch_feed", return_value=[feed_entry]),
            patch("app.tasks.signal_tasks.score_relevance", return_value=0.05),
        ):
            from app.tasks.signal_tasks import poll_signal_feeds

            result = poll_signal_feeds()
            assert result["status"] == "ok"
            assert result["created"] == 0


@pytest.mark.skipif(not HAS_FEEDPARSER, reason="feedparser not installed")
class TestSendSignalDigest:
    def test_no_subscriptions_sends_nothing(self):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        with patch(
            "app.tasks.signal_tasks.get_celery_session_context",
            _mock_session_ctx(mock_session),
        ):
            from app.tasks.signal_tasks import send_signal_digest

            result = send_signal_digest()
            assert result["status"] == "ok"
            assert result["sent"] == 0
