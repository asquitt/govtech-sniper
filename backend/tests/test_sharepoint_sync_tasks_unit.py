"""
Unit tests for sharepoint_sync_tasks Celery tasks.
Tests _sync_proposal and _watch_folders standalone async helpers.
"""

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch


def _mock_session_ctx(mock_session):
    @asynccontextmanager
    async def _ctx():
        yield mock_session

    return _ctx


class TestSyncProposal:
    def test_config_not_found(self):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with patch(
            "app.tasks.sharepoint_sync_tasks.get_celery_session_context",
            _mock_session_ctx(mock_session),
        ):
            from app.tasks.sharepoint_sync_tasks import _sync_proposal

            result = asyncio.run(_sync_proposal(config_id=9999))
            assert "error" in result
            assert "Config not found" in result["error"]

    def test_proposal_not_found(self):
        mock_config = MagicMock()
        mock_config.proposal_id = 999

        mock_session = AsyncMock()
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalar_one_or_none.return_value = mock_config
            else:
                result.scalar_one_or_none.return_value = None
            return result

        mock_session.execute = AsyncMock(side_effect=side_effect)

        with patch(
            "app.tasks.sharepoint_sync_tasks.get_celery_session_context",
            _mock_session_ctx(mock_session),
        ):
            from app.tasks.sharepoint_sync_tasks import _sync_proposal

            result = asyncio.run(_sync_proposal(config_id=1))
            assert "error" in result
            assert "Proposal not found" in result["error"]

    def test_no_integration_logs_failure(self):
        mock_config = MagicMock()
        mock_config.proposal_id = 1
        mock_config.user_id = 1

        mock_proposal = MagicMock()
        mock_proposal.id = 1

        mock_session = AsyncMock()
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalar_one_or_none.return_value = mock_config
            elif call_count == 2:
                result.scalar_one_or_none.return_value = mock_proposal
            else:
                result.scalar_one_or_none.return_value = None
            return result

        mock_session.execute = AsyncMock(side_effect=side_effect)

        with patch(
            "app.tasks.sharepoint_sync_tasks.get_celery_session_context",
            _mock_session_ctx(mock_session),
        ):
            from app.tasks.sharepoint_sync_tasks import _sync_proposal

            result = asyncio.run(_sync_proposal(config_id=1))
            assert "error" in result
            assert "No SharePoint integration" in result["error"]
            mock_session.add.assert_called()


class TestWatchFolders:
    def test_no_configs_returns_empty(self):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        with patch(
            "app.tasks.sharepoint_sync_tasks.get_celery_session_context",
            _mock_session_ctx(mock_session),
        ):
            from app.tasks.sharepoint_sync_tasks import _watch_folders

            result = asyncio.run(_watch_folders())
            assert result["detected"] == 0
            assert result["configs_checked"] == 0
            assert result["errors"] == 0

    def test_no_integration_skips_config(self):
        mock_config = MagicMock()
        mock_config.id = 1
        mock_config.user_id = 1

        mock_session = AsyncMock()
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalars.return_value.all.return_value = [mock_config]
            else:
                result.scalar_one_or_none.return_value = None
            return result

        mock_session.execute = AsyncMock(side_effect=side_effect)

        with patch(
            "app.tasks.sharepoint_sync_tasks.get_celery_session_context",
            _mock_session_ctx(mock_session),
        ):
            from app.tasks.sharepoint_sync_tasks import _watch_folders

            result = asyncio.run(_watch_folders())
            assert result["detected"] == 0
            assert result["configs_checked"] == 1
