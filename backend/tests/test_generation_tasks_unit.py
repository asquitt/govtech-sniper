"""
Unit tests for generation_tasks Celery tasks.
Tests generate_proposal_section, generate_all_sections, refresh_context_cache,
and generate_proposal_outline_async.
"""

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch


def _mock_session_ctx(mock_session):
    @asynccontextmanager
    async def _ctx():
        yield mock_session

    return _ctx


class TestGenerateProposalSection:
    def test_section_not_found(self):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with (
            patch(
                "app.tasks.generation_tasks.get_celery_session_context",
                _mock_session_ctx(mock_session),
            ),
            patch("app.tasks.generation_tasks.GeminiService"),
        ):
            from app.tasks.generation_tasks import generate_proposal_section

            result = generate_proposal_section.apply(
                kwargs={"section_id": 9999, "user_id": 1},
            )
            assert result.result["status"] == "error"
            assert "not found" in result.result["error"]


class TestGenerateAllSections:
    def test_no_pending_sections(self):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        with patch(
            "app.tasks.generation_tasks.get_celery_session_context",
            _mock_session_ctx(mock_session),
        ):
            from app.tasks.generation_tasks import generate_all_sections

            result = generate_all_sections.apply(
                kwargs={"proposal_id": 1, "user_id": 1},
            )
            assert result.result["status"] == "queued"
            assert result.result["sections_queued"] == 0


class TestRefreshContextCache:
    def test_no_documents_skips(self):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        with (
            patch(
                "app.tasks.generation_tasks.get_celery_session_context",
                _mock_session_ctx(mock_session),
            ),
            patch("app.tasks.generation_tasks.GeminiService"),
        ):
            from app.tasks.generation_tasks import refresh_context_cache

            result = refresh_context_cache.apply(kwargs={"user_id": 1})
            assert result.result["status"] == "skipped"

    def test_cache_creation_failed(self):
        mock_doc = MagicMock()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_doc]
        mock_session.execute.return_value = mock_result

        mock_gemini = MagicMock()
        mock_gemini.create_context_cache = AsyncMock(return_value=None)

        with (
            patch(
                "app.tasks.generation_tasks.get_celery_session_context",
                _mock_session_ctx(mock_session),
            ),
            patch("app.tasks.generation_tasks.GeminiService", return_value=mock_gemini),
        ):
            from app.tasks.generation_tasks import refresh_context_cache

            result = refresh_context_cache.apply(kwargs={"user_id": 1})
            assert result.result["status"] == "failed"


class TestGenerateProposalOutlineAsync:
    """Test the standalone async function directly."""

    def test_proposal_not_found(self):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with patch("app.tasks.generation_tasks.GeminiService"):
            from app.tasks.generation_tasks import generate_proposal_outline_async

            result = asyncio.run(
                generate_proposal_outline_async(
                    proposal_id=9999,
                    user_id=1,
                    task_id="test-task-id",
                    session_override=mock_session,
                )
            )
            assert result["status"] == "error"
            assert "not found" in result["error"]

    def test_no_compliance_matrix(self):
        mock_proposal = MagicMock()
        mock_proposal.rfp_id = 1

        mock_session = AsyncMock()
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalar_one_or_none.return_value = mock_proposal
            else:
                result.scalar_one_or_none.return_value = None
            return result

        mock_session.execute = AsyncMock(side_effect=side_effect)

        with patch("app.tasks.generation_tasks.GeminiService"):
            from app.tasks.generation_tasks import generate_proposal_outline_async

            result = asyncio.run(
                generate_proposal_outline_async(
                    proposal_id=1,
                    user_id=1,
                    task_id="test-task-id",
                    session_override=mock_session,
                )
            )
            assert result["status"] == "error"
            assert "compliance matrix" in result["error"].lower()
