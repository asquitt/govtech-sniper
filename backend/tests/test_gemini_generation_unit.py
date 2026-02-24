"""
Unit tests for gemini_service/generation.py — rewrite, expand, outline, citations, health check.

Tests use mock_ai=True to verify mapping logic without hitting Gemini API.
"""

from types import SimpleNamespace

import pytest

from app.services.gemini_service import GeminiService


def _make_service() -> GeminiService:
    """Create a GeminiService with mock_ai enabled."""
    service = GeminiService(api_key=None)
    return service


class TestExtractCitations:
    """GeminiGenerationMixin._extract_citations"""

    def test_no_citations(self):
        service = _make_service()
        assert service._extract_citations("No citations here.") == []

    def test_single_citation(self):
        service = _make_service()
        text = "The contractor shall [[Source: capability.pdf, Page 12]] provide services."
        citations = service._extract_citations(text)
        assert len(citations) == 1
        assert citations[0].source_file == "capability.pdf"
        assert citations[0].page_number == 12

    def test_multiple_citations(self):
        service = _make_service()
        text = (
            "As per [[Source: past_perf.pdf, Page 3]], "
            "we demonstrated [[Source: capability.pdf, Page 7]] our approach."
        )
        citations = service._extract_citations(text)
        assert len(citations) == 2
        files = {c.source_file for c in citations}
        assert "past_perf.pdf" in files
        assert "capability.pdf" in files

    def test_deduplicates_citations(self):
        service = _make_service()
        text = "[[Source: doc.pdf, Page 1]] first ref. [[Source: doc.pdf, Page 1]] duplicate ref."
        citations = service._extract_citations(text)
        assert len(citations) == 1

    def test_citation_without_page(self):
        service = _make_service()
        text = "See [[Source: overview.pdf]] for details."
        citations = service._extract_citations(text)
        assert len(citations) == 1
        assert citations[0].source_file == "overview.pdf"
        assert citations[0].page_number is None


class TestRewriteSection:
    """GeminiGenerationMixin.rewrite_section — mock mode"""

    @pytest.mark.asyncio
    async def test_mock_rewrite(self, monkeypatch):
        monkeypatch.setattr("app.services.gemini_service.generation.settings.mock_ai", True)
        service = _make_service()

        result = await service.rewrite_section(
            content="The contractor provides cybersecurity services.",
            requirement_text="Provide IT security",
            tone="formal",
        )

        assert result.raw_text.startswith("[Rewritten]")
        assert result.model_used == "mock"
        assert result.tokens_used == 0
        assert result.generation_time_seconds == 0.0

    @pytest.mark.asyncio
    async def test_mock_rewrite_preserves_content(self, monkeypatch):
        monkeypatch.setattr("app.services.gemini_service.generation.settings.mock_ai", True)
        service = _make_service()

        original = "Our team has 10 years of experience."
        result = await service.rewrite_section(
            content=original,
            requirement_text="Experience requirement",
        )

        assert original in result.raw_text

    @pytest.mark.asyncio
    async def test_rewrite_no_model_raises(self, monkeypatch):
        monkeypatch.setattr("app.services.gemini_service.generation.settings.mock_ai", False)
        service = _make_service()
        service.pro_model = None

        with pytest.raises(ValueError, match="not available"):
            await service.rewrite_section(
                content="test",
                requirement_text="test",
            )


class TestExpandSection:
    """GeminiGenerationMixin.expand_section — mock mode"""

    @pytest.mark.asyncio
    async def test_mock_expand(self, monkeypatch):
        monkeypatch.setattr("app.services.gemini_service.generation.settings.mock_ai", True)
        service = _make_service()

        result = await service.expand_section(
            content="Brief intro to our capabilities.",
            requirement_text="Technical approach",
            target_words=500,
        )

        assert "[Expanded" in result.raw_text
        assert result.model_used == "mock"

    @pytest.mark.asyncio
    async def test_expand_no_model_raises(self, monkeypatch):
        monkeypatch.setattr("app.services.gemini_service.generation.settings.mock_ai", False)
        service = _make_service()
        service.pro_model = None

        with pytest.raises(ValueError, match="not available"):
            await service.expand_section(
                content="test",
                requirement_text="test",
            )


class TestGenerateOutline:
    """GeminiGenerationMixin.generate_outline — mock mode"""

    @pytest.mark.asyncio
    async def test_mock_outline(self, monkeypatch):
        monkeypatch.setattr("app.services.gemini_service.generation.settings.mock_ai", True)
        service = _make_service()

        result = await service.generate_outline(
            requirements_json='[{"id": "REQ-001"}]',
            rfp_summary="Test RFP for cybersecurity services",
        )

        assert "sections" in result
        assert len(result["sections"]) >= 2
        titles = {s["title"] for s in result["sections"]}
        assert "Executive Summary" in titles
        assert "Technical Approach" in titles

    @pytest.mark.asyncio
    async def test_outline_no_model_raises(self, monkeypatch):
        monkeypatch.setattr("app.services.gemini_service.generation.settings.mock_ai", False)
        service = _make_service()
        service.pro_model = None

        with pytest.raises(ValueError, match="not configured"):
            await service.generate_outline(
                requirements_json="[]",
                rfp_summary="test",
            )


class TestCountTokens:
    """GeminiGenerationMixin.count_tokens"""

    @pytest.mark.asyncio
    async def test_no_model_fallback(self):
        service = _make_service()
        service.pro_model = None

        count = await service.count_tokens("Hello world this is a test")
        # Fallback: len(text) // 4
        assert count == len("Hello world this is a test") // 4

    @pytest.mark.asyncio
    async def test_with_model(self):
        service = _make_service()
        mock_model = SimpleNamespace()
        mock_model.count_tokens_async = lambda text: _async_return(SimpleNamespace(total_tokens=42))
        service.pro_model = mock_model

        count = await service.count_tokens("Test text")
        assert count == 42

    @pytest.mark.asyncio
    async def test_model_error_fallback(self):
        service = _make_service()
        mock_model = SimpleNamespace()

        async def _fail(text):
            raise RuntimeError("API error")

        mock_model.count_tokens_async = _fail
        service.pro_model = mock_model

        count = await service.count_tokens("Some text here")
        assert count == len("Some text here") // 4


class TestHealthCheck:
    """GeminiGenerationMixin.health_check"""

    @pytest.mark.asyncio
    async def test_mock_mode(self, monkeypatch):
        monkeypatch.setattr("app.services.gemini_service.generation.settings.mock_ai", True)
        service = _make_service()
        assert await service.health_check() is True

    @pytest.mark.asyncio
    async def test_no_flash_model(self, monkeypatch):
        monkeypatch.setattr("app.services.gemini_service.generation.settings.mock_ai", False)
        service = _make_service()
        service.flash_model = None
        assert await service.health_check() is False

    @pytest.mark.asyncio
    async def test_flash_model_success(self, monkeypatch):
        monkeypatch.setattr("app.services.gemini_service.generation.settings.mock_ai", False)
        service = _make_service()

        mock_model = SimpleNamespace()
        mock_model.generate_content_async = lambda *a, **kw: _async_return(
            SimpleNamespace(text="OK")
        )
        service.flash_model = mock_model

        assert await service.health_check() is True


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


class TestPromptTemplates:
    """Verify prompt templates have expected placeholders."""

    def test_rewrite_prompt_placeholders(self):
        from app.services.gemini_service.prompts import REWRITE_PROMPT

        assert "{content}" in REWRITE_PROMPT
        assert "{requirement_text}" in REWRITE_PROMPT
        assert "{tone}" in REWRITE_PROMPT
        assert "{custom_instructions}" in REWRITE_PROMPT

    def test_expand_prompt_placeholders(self):
        from app.services.gemini_service.prompts import EXPAND_PROMPT

        assert "{content}" in EXPAND_PROMPT
        assert "{requirement_text}" in EXPAND_PROMPT
        assert "{target_words}" in EXPAND_PROMPT
        assert "{focus_instructions}" in EXPAND_PROMPT

    def test_outline_prompt_placeholders(self):
        from app.services.gemini_service.prompts import OUTLINE_PROMPT

        assert "{requirements_json}" in OUTLINE_PROMPT
        assert "{rfp_summary}" in OUTLINE_PROMPT

    def test_generation_prompt_placeholders(self):
        from app.services.gemini_service.prompts import GENERATION_PROMPT

        assert "{requirement_text}" in GENERATION_PROMPT
        assert "{section}" in GENERATION_PROMPT
        assert "{tone}" in GENERATION_PROMPT

    def test_deep_read_prompt_placeholders(self):
        from app.services.gemini_service.prompts import DEEP_READ_PROMPT

        assert "{rfp_text}" in DEEP_READ_PROMPT


# ---------------------------------------------------------------------------
# Settings proxy
# ---------------------------------------------------------------------------


class TestSettingsProxy:
    def test_delegates_to_app_config(self):
        from app.services.gemini_service import settings

        # mock_ai should be accessible via the proxy
        assert hasattr(settings, "mock_ai")


# ---------------------------------------------------------------------------
# Async helper
# ---------------------------------------------------------------------------


async def _async_return(value):
    return value
