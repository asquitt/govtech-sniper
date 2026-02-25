"""
Unit tests for analysis_tasks Celery tasks.
Tests run_async helper and core task logic via module-level functions.
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.rfp import RFPStatus
from app.tasks.analysis_tasks import run_async


def _mock_session_ctx(mock_session):
    @asynccontextmanager
    async def _ctx():
        yield mock_session

    return _ctx


class TestRunAsync:
    def test_executes_coroutine(self):
        async def coro():
            return 42

        assert run_async(coro()) == 42

    def test_propagates_exceptions(self):
        async def coro():
            raise ValueError("test error")

        try:
            run_async(coro())
            raise AssertionError("Should have raised")
        except ValueError as e:
            assert "test error" in str(e)


class TestAnalyzeRfpLogic:
    """Test analyze_rfp task logic by calling through Celery eager mode."""

    def test_rfp_not_found_returns_error(self):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with (
            patch(
                "app.tasks.analysis_tasks.get_celery_session_context",
                _mock_session_ctx(mock_session),
            ),
            patch("app.tasks.analysis_tasks.GeminiService"),
            patch("app.tasks.analysis_tasks.celery_app") as mock_celery,
        ):
            # Re-define the task logic inline to avoid Celery wrapping issues
            from app.tasks.analysis_tasks import analyze_rfp

            mock_celery.conf.task_always_eager = True
            result = analyze_rfp.apply(kwargs={"rfp_id": 9999})
            assert result.result["status"] == "error"
            assert "not found" in result.result["error"]

    def test_already_analyzed_skips(self):
        mock_rfp = MagicMock()
        mock_rfp.status = RFPStatus.ANALYZED

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_rfp
        mock_session.execute.return_value = mock_result

        with (
            patch(
                "app.tasks.analysis_tasks.get_celery_session_context",
                _mock_session_ctx(mock_session),
            ),
            patch("app.tasks.analysis_tasks.GeminiService"),
        ):
            from app.tasks.analysis_tasks import analyze_rfp

            result = analyze_rfp.apply(kwargs={"rfp_id": 1, "force_reanalyze": False})
            assert result.result["status"] == "skipped"

    def test_no_text_returns_error(self):
        mock_rfp = MagicMock()
        mock_rfp.status = RFPStatus.NEW
        mock_rfp.full_text = None
        mock_rfp.description = None

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_rfp
        mock_session.execute.return_value = mock_result

        with (
            patch(
                "app.tasks.analysis_tasks.get_celery_session_context",
                _mock_session_ctx(mock_session),
            ),
            patch("app.tasks.analysis_tasks.GeminiService"),
        ):
            from app.tasks.analysis_tasks import analyze_rfp

            result = analyze_rfp.apply(kwargs={"rfp_id": 1})
            assert result.result["status"] == "error"
            assert "No text" in result.result["error"]


class TestRunKillerFilterLogic:
    def test_rfp_not_found(self):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with (
            patch(
                "app.tasks.analysis_tasks.get_celery_session_context",
                _mock_session_ctx(mock_session),
            ),
            patch("app.tasks.analysis_tasks.KillerFilterService"),
        ):
            from app.tasks.analysis_tasks import run_killer_filter

            result = run_killer_filter.apply(kwargs={"rfp_id": 9999, "user_id": 1})
            assert result.result["status"] == "error"
            assert "not found" in result.result["error"]

    def test_profile_not_found(self):
        mock_rfp = MagicMock()
        mock_session = AsyncMock()
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalar_one_or_none.return_value = mock_rfp
            else:
                result.scalar_one_or_none.return_value = None
            return result

        mock_session.execute = AsyncMock(side_effect=side_effect)

        with (
            patch(
                "app.tasks.analysis_tasks.get_celery_session_context",
                _mock_session_ctx(mock_session),
            ),
            patch("app.tasks.analysis_tasks.KillerFilterService"),
        ):
            from app.tasks.analysis_tasks import run_killer_filter

            result = run_killer_filter.apply(kwargs={"rfp_id": 1, "user_id": 1})
            assert result.result["status"] == "error"
            assert "profile" in result.result["error"].lower()

    def test_filter_success(self):
        mock_rfp = MagicMock()
        mock_profile = MagicMock()
        mock_filter_result = MagicMock()
        mock_filter_result.is_qualified = True
        mock_filter_result.reason = "Good match"
        mock_filter_result.confidence = 0.9
        mock_filter_result.disqualifying_factors = []
        mock_filter_result.matching_factors = ["NAICS match"]

        mock_session = AsyncMock()
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalar_one_or_none.return_value = mock_rfp
            else:
                result.scalar_one_or_none.return_value = mock_profile
            return result

        mock_session.execute = AsyncMock(side_effect=side_effect)
        mock_filter_svc = MagicMock()
        mock_filter_svc.filter_rfp = AsyncMock(return_value=mock_filter_result)

        with (
            patch(
                "app.tasks.analysis_tasks.get_celery_session_context",
                _mock_session_ctx(mock_session),
            ),
            patch("app.tasks.analysis_tasks.KillerFilterService", return_value=mock_filter_svc),
        ):
            from app.tasks.analysis_tasks import run_killer_filter

            result = run_killer_filter.apply(kwargs={"rfp_id": 1, "user_id": 1})
            assert result.result["status"] == "completed"
            assert result.result["is_qualified"] is True
            assert result.result["confidence"] == 0.9
