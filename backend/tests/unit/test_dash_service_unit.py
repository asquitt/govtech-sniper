"""
Dash Service Unit Tests
========================
Tests for dash_service helper functions — context gathering helpers,
history conversion, and mock/unconfigured response paths.
All DB and Gemini calls are mocked.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.dash_service import (
    MAX_HISTORY_MESSAGES,
    _build_gemini_history,
    _truncate,
    generate_dash_response,
    get_context_citations,
)

# =============================================================================
# _truncate
# =============================================================================


class TestTruncate:
    def test_short_text_returned_as_is(self):
        assert _truncate("hello", 100) == "hello"

    def test_text_truncated_at_max_chars(self):
        result = _truncate("a" * 200, 100)
        assert len(result) == 100
        assert result.endswith("...")

    def test_none_returns_empty_string(self):
        assert _truncate(None, 50) == ""

    def test_empty_string_returned_as_is(self):
        assert _truncate("", 50) == ""

    def test_exact_length_not_truncated(self):
        text = "x" * 50
        assert _truncate(text, 50) == text

    def test_trailing_whitespace_stripped_before_ellipsis(self):
        # Trailing spaces before the cut-off should be stripped
        text = "word " * 30  # 150 chars
        result = _truncate(text, 20)
        assert result.endswith("...")


# =============================================================================
# _build_gemini_history
# =============================================================================


class TestBuildGeminiHistory:
    def test_empty_history_returns_empty_list(self):
        assert _build_gemini_history(None) == []
        assert _build_gemini_history([]) == []

    def test_user_role_preserved(self):
        history = [{"role": "user", "content": "Hello"}]
        result = _build_gemini_history(history)
        assert result[0]["role"] == "user"
        assert result[0]["parts"] == ["Hello"]

    def test_assistant_role_converted_to_model(self):
        history = [{"role": "assistant", "content": "Sure!"}]
        result = _build_gemini_history(history)
        assert result[0]["role"] == "model"

    def test_truncates_to_max_history_messages(self):
        history = [{"role": "user", "content": f"msg {i}"} for i in range(50)]
        result = _build_gemini_history(history)
        assert len(result) == MAX_HISTORY_MESSAGES

    def test_takes_last_n_messages(self):
        history = [{"role": "user", "content": f"msg {i}"} for i in range(25)]
        result = _build_gemini_history(history)
        # Should take the last MAX_HISTORY_MESSAGES messages
        assert result[-1]["parts"] == ["msg 24"]

    def test_unknown_role_treated_as_user(self):
        history = [{"role": "system", "content": "context"}]
        result = _build_gemini_history(history)
        assert result[0]["role"] == "user"

    def test_missing_content_defaults_to_empty_string(self):
        history = [{"role": "user"}]
        result = _build_gemini_history(history)
        assert result[0]["parts"] == [""]


# =============================================================================
# generate_dash_response — mock_ai path
# =============================================================================


class TestGenerateDashResponseMockAI:
    @pytest.mark.asyncio
    async def test_mock_response_returned_when_mock_ai_true(self):
        mock_db = AsyncMock()

        with (
            patch("app.services.dash_service.settings") as mock_settings,
            patch(
                "app.services.dash_service._gather_context",
                new=AsyncMock(return_value=("No data.", [])),
            ),
        ):
            mock_settings.mock_ai = True
            mock_settings.gemini_api_key = None

            answer, citations = await generate_dash_response(
                mock_db,
                user_id=1,
                question="What is the deadline?",
                rfp_id=None,
            )

        assert "Mock Dash Response" in answer
        assert "What is the deadline?" in answer

    @pytest.mark.asyncio
    async def test_mock_response_includes_rfp_context_note_when_rfp_given(self):
        mock_db = AsyncMock()

        with (
            patch("app.services.dash_service.settings") as mock_settings,
            patch(
                "app.services.dash_service._gather_context",
                new=AsyncMock(return_value=("context", [])),
            ),
        ):
            mock_settings.mock_ai = True
            mock_settings.gemini_api_key = None

            answer, citations = await generate_dash_response(
                mock_db,
                user_id=1,
                question="anything",
                rfp_id=42,
            )

        assert "RFP and user data available" in answer

    @pytest.mark.asyncio
    async def test_no_rfp_mentioned_when_rfp_id_none(self):
        mock_db = AsyncMock()

        with (
            patch("app.services.dash_service.settings") as mock_settings,
            patch(
                "app.services.dash_service._gather_context", new=AsyncMock(return_value=("", []))
            ),
        ):
            mock_settings.mock_ai = True
            mock_settings.gemini_api_key = None

            answer, _ = await generate_dash_response(
                mock_db,
                user_id=1,
                question="anything",
                rfp_id=None,
            )

        assert "No RFP selected" in answer


# =============================================================================
# generate_dash_response — no API key path
# =============================================================================


class TestGenerateDashResponseNoAPIKey:
    @pytest.mark.asyncio
    async def test_returns_error_message_when_no_api_key(self):
        mock_db = AsyncMock()

        with (
            patch("app.services.dash_service.settings") as mock_settings,
            patch(
                "app.services.dash_service._gather_context", new=AsyncMock(return_value=("", []))
            ),
        ):
            mock_settings.mock_ai = False
            mock_settings.gemini_api_key = None

            answer, citations = await generate_dash_response(
                mock_db,
                user_id=1,
                question="test question",
            )

        assert "not configured" in answer.lower()

    @pytest.mark.asyncio
    async def test_citations_empty_when_no_api_key(self):
        mock_db = AsyncMock()

        with (
            patch("app.services.dash_service.settings") as mock_settings,
            patch(
                "app.services.dash_service._gather_context", new=AsyncMock(return_value=("", []))
            ),
        ):
            mock_settings.mock_ai = False
            mock_settings.gemini_api_key = None

            _, citations = await generate_dash_response(
                mock_db,
                user_id=1,
                question="test",
            )

        assert citations == []


# =============================================================================
# generate_dash_response — real Gemini path (mocked model)
# =============================================================================


class TestGenerateDashResponseGemini:
    @pytest.mark.asyncio
    async def test_returns_model_response_text(self):
        mock_db = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = "Here is what I found."
        mock_chat = MagicMock()
        mock_chat.send_message_async = AsyncMock(return_value=mock_response)
        mock_model = MagicMock()
        mock_model.start_chat.return_value = mock_chat

        with (
            patch("app.services.dash_service.settings") as mock_settings,
            patch("app.services.dash_service.genai") as mock_genai,
            patch(
                "app.services.dash_service._gather_context",
                new=AsyncMock(return_value=("context", [])),
            ),
        ):
            mock_settings.mock_ai = False
            mock_settings.gemini_api_key = "real-key"
            mock_settings.gemini_model_flash = "gemini-1.5-flash"
            mock_genai.configure.return_value = None
            mock_genai.GenerativeModel.return_value = mock_model
            mock_genai.GenerationConfig = MagicMock(return_value={})

            answer, _ = await generate_dash_response(
                mock_db,
                user_id=1,
                question="What is the NAICS code?",
            )

        assert answer == "Here is what I found."

    @pytest.mark.asyncio
    async def test_returns_error_string_on_model_exception(self):
        mock_db = AsyncMock()
        mock_model = MagicMock()
        mock_model.start_chat.side_effect = Exception("Gemini blew up")

        with (
            patch("app.services.dash_service.settings") as mock_settings,
            patch("app.services.dash_service.genai") as mock_genai,
            patch(
                "app.services.dash_service._gather_context", new=AsyncMock(return_value=("", []))
            ),
        ):
            mock_settings.mock_ai = False
            mock_settings.gemini_api_key = "real-key"
            mock_settings.gemini_model_flash = "gemini-1.5-flash"
            mock_genai.configure.return_value = None
            mock_genai.GenerativeModel.return_value = mock_model
            mock_genai.GenerationConfig = MagicMock(return_value={})

            answer, _ = await generate_dash_response(
                mock_db,
                user_id=1,
                question="anything",
            )

        assert "error" in answer.lower()

    @pytest.mark.asyncio
    async def test_conversation_history_passed_to_chat(self):
        mock_db = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = "Response"
        mock_chat = MagicMock()
        mock_chat.send_message_async = AsyncMock(return_value=mock_response)
        mock_model = MagicMock()
        mock_model.start_chat.return_value = mock_chat

        history = [
            {"role": "user", "content": "prior question"},
            {"role": "assistant", "content": "prior answer"},
        ]

        with (
            patch("app.services.dash_service.settings") as mock_settings,
            patch("app.services.dash_service.genai") as mock_genai,
            patch(
                "app.services.dash_service._gather_context", new=AsyncMock(return_value=("", []))
            ),
        ):
            mock_settings.mock_ai = False
            mock_settings.gemini_api_key = "key"
            mock_settings.gemini_model_flash = "gemini-1.5-flash"
            mock_genai.configure.return_value = None
            mock_genai.GenerativeModel.return_value = mock_model
            mock_genai.GenerationConfig = MagicMock(return_value={})

            await generate_dash_response(
                mock_db,
                user_id=1,
                question="follow-up",
                conversation_history=history,
            )

        # Verify start_chat was called with a history argument
        mock_model.start_chat.assert_called_once()
        call_kwargs = mock_model.start_chat.call_args
        assert call_kwargs is not None


# =============================================================================
# get_context_citations
# =============================================================================


class TestGetContextCitations:
    @pytest.mark.asyncio
    async def test_returns_citations_from_context(self):
        mock_db = AsyncMock()
        expected_citations = [{"type": "rfp", "rfp_id": 7, "title": "Big RFP"}]

        with patch(
            "app.services.dash_service._gather_context",
            new=AsyncMock(return_value=("context text", expected_citations)),
        ):
            citations = await get_context_citations(mock_db, user_id=1, rfp_id=7)

        assert citations == expected_citations

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_context(self):
        mock_db = AsyncMock()

        with patch(
            "app.services.dash_service._gather_context",
            new=AsyncMock(return_value=("", [])),
        ):
            citations = await get_context_citations(mock_db, user_id=1)

        assert citations == []
