"""
Dash Service Unit Tests
========================
Tests for pure helper functions: _truncate and _build_gemini_history.
"""

from app.services.dash_service import _build_gemini_history, _truncate

# ---------------------------------------------------------------------------
# _truncate
# ---------------------------------------------------------------------------


class TestTruncate:
    def test_short_text(self):
        assert _truncate("hello", 100) == "hello"

    def test_exact_limit(self):
        text = "a" * 50
        assert _truncate(text, 50) == text

    def test_truncates_long_text(self):
        text = "a" * 100
        result = _truncate(text, 50)
        assert len(result) <= 50
        assert result.endswith("...")

    def test_none(self):
        assert _truncate(None, 100) == ""

    def test_empty(self):
        assert _truncate("", 100) == ""


# ---------------------------------------------------------------------------
# _build_gemini_history
# ---------------------------------------------------------------------------


class TestBuildGeminiHistory:
    def test_empty_history(self):
        assert _build_gemini_history(None) == []
        assert _build_gemini_history([]) == []

    def test_converts_roles(self):
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        result = _build_gemini_history(history)
        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[0]["parts"] == ["Hello"]
        assert result[1]["role"] == "model"
        assert result[1]["parts"] == ["Hi there"]

    def test_truncates_to_max(self):
        # MAX_HISTORY_MESSAGES is 20
        history = [{"role": "user", "content": f"msg {i}"} for i in range(30)]
        result = _build_gemini_history(history)
        assert len(result) == 20

    def test_keeps_latest_messages(self):
        history = [{"role": "user", "content": f"msg {i}"} for i in range(25)]
        result = _build_gemini_history(history)
        # Should have the last 20 messages (indexes 5-24)
        assert result[0]["parts"] == ["msg 5"]
        assert result[-1]["parts"] == ["msg 24"]

    def test_handles_missing_fields(self):
        history = [{"role": "user"}, {}]
        result = _build_gemini_history(history)
        assert result[0]["parts"] == [""]
        assert result[1]["role"] == "user"
        assert result[1]["parts"] == [""]
