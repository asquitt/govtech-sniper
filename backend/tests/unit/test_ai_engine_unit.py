"""
AI Engine Unit Tests
=====================
Tests for AIEngine — citation extraction, prompt construction, validation,
and token counting. All Gemini API calls are mocked.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai_engine import AIEngine, ExtractedRequirement

# =============================================================================
# Fixtures
# =============================================================================


def make_engine() -> AIEngine:
    """Create an AIEngine with a fake API key without hitting genai.configure."""
    with patch("app.services.ai_engine.genai") as mock_genai:
        mock_genai.configure.return_value = None
        mock_genai.GenerativeModel.return_value = MagicMock()
        mock_genai.GenerationConfig = MagicMock(return_value={})
        engine = AIEngine(api_key="fake-key")
    return engine


def make_requirement(**kwargs) -> ExtractedRequirement:
    defaults = dict(
        id="REQ-001",
        section="L.5.2.1",
        text="The offeror shall demonstrate past performance.",
        requirement_type="Technical",
        importance="Mandatory",
        page_reference=12,
    )
    defaults.update(kwargs)
    return ExtractedRequirement(**defaults)


# =============================================================================
# Initialization
# =============================================================================


class TestAIEngineInit:
    def test_initialized_true_with_api_key(self):
        with patch("app.services.ai_engine.genai"):
            engine = AIEngine(api_key="test-key")
        assert engine._initialized is True

    def test_initialized_false_without_api_key(self):
        with patch("app.services.ai_engine.settings") as mock_settings:
            mock_settings.gemini_api_key = None
            engine = AIEngine(api_key=None)
        assert engine._initialized is False

    def test_ensure_initialized_raises_when_not_initialized(self):
        with patch("app.services.ai_engine.settings") as mock_settings:
            mock_settings.gemini_api_key = None
            engine = AIEngine(api_key=None)
        with pytest.raises(RuntimeError, match="not initialized"):
            engine._ensure_initialized()

    def test_ensure_initialized_silent_when_initialized(self):
        with patch("app.services.ai_engine.genai"):
            engine = AIEngine(api_key="key")
        engine._ensure_initialized()  # should not raise


# =============================================================================
# Citation extraction
# =============================================================================


class TestExtractCitations:
    def setup_method(self):
        with patch("app.services.ai_engine.genai"):
            self.engine = AIEngine(api_key="test")

    def test_extracts_citation_with_page(self):
        text = "Our team has done this work [[Source: Report.pdf, Page 5]] before."
        citations = self.engine._extract_citations(text)
        assert len(citations) == 1
        assert citations[0].source_file == "Report.pdf"
        assert citations[0].page_number == 5

    def test_extracts_citation_without_page(self):
        text = "Evidence here [[Source: Evidence.pdf]] supports the claim."
        citations = self.engine._extract_citations(text)
        assert len(citations) == 1
        assert citations[0].source_file == "Evidence.pdf"
        assert citations[0].page_number is None

    def test_extracts_multiple_citations(self):
        text = "First [[Source: A.pdf, Page 1]] and second [[Source: B.pdf, Page 2]] cited."
        citations = self.engine._extract_citations(text)
        assert len(citations) == 2
        assert citations[0].source_file == "A.pdf"
        assert citations[1].source_file == "B.pdf"

    def test_returns_empty_list_when_no_citations(self):
        text = "No citations here at all."
        citations = self.engine._extract_citations(text)
        assert citations == []

    def test_citation_raw_text_matches_pattern(self):
        text = "Claim [[Source: Doc.pdf, Page 10]] done."
        citations = self.engine._extract_citations(text)
        assert citations[0].raw_text == "[[Source: Doc.pdf, Page 10]]"

    def test_citation_positions_correct(self):
        text = "Pre [[Source: F.pdf, Page 3]] post"
        citations = self.engine._extract_citations(text)
        assert citations[0].start_pos == 4
        assert text[citations[0].start_pos : citations[0].end_pos] == "[[Source: F.pdf, Page 3]]"

    def test_citation_with_page_keyword_lowercase(self):
        text = "See [[Source: Manual.pdf, page 7]] for details."
        citations = self.engine._extract_citations(text)
        assert len(citations) == 1
        assert citations[0].page_number == 7

    def test_source_file_stripped_of_whitespace(self):
        text = "Ref [[Source:  SpaceyFile.pdf , Page 2]] here."
        citations = self.engine._extract_citations(text)
        assert citations[0].source_file == "SpaceyFile.pdf"


# =============================================================================
# validate_citations
# =============================================================================


class TestValidateCitations:
    def setup_method(self):
        with patch("app.services.ai_engine.genai"):
            self.engine = AIEngine(api_key="test")

    @pytest.mark.asyncio
    async def test_valid_citation_matched_by_exact_name(self):
        text = "Proof [[Source: PastPerf.pdf, Page 4]] here."
        valid, invalid = await self.engine.validate_citations(text, ["PastPerf.pdf"])
        assert len(valid) == 1
        assert len(invalid) == 0

    @pytest.mark.asyncio
    async def test_invalid_citation_not_in_sources(self):
        text = "Claim [[Source: Ghost.pdf, Page 1]] done."
        valid, invalid = await self.engine.validate_citations(text, ["PastPerf.pdf"])
        assert len(valid) == 0
        assert len(invalid) == 1

    @pytest.mark.asyncio
    async def test_case_insensitive_matching(self):
        text = "Ref [[Source: pastperf.pdf, Page 2]] here."
        valid, invalid = await self.engine.validate_citations(text, ["PastPerf.pdf"])
        assert len(valid) == 1

    @pytest.mark.asyncio
    async def test_empty_sources_marks_all_invalid(self):
        text = "Ref [[Source: Any.pdf, Page 1]] here."
        valid, invalid = await self.engine.validate_citations(text, [])
        assert len(valid) == 0
        assert len(invalid) == 1


# =============================================================================
# count_tokens
# =============================================================================


class TestCountTokens:
    def test_fallback_estimate_when_not_initialized(self):
        with patch("app.services.ai_engine.settings") as mock_settings:
            mock_settings.gemini_api_key = None
            AIEngine(api_key=None)

    @pytest.mark.asyncio
    async def test_fallback_estimate_formula(self):
        with patch("app.services.ai_engine.settings") as mock_settings:
            mock_settings.gemini_api_key = None
            engine = AIEngine(api_key=None)
        result = await engine.count_tokens("a" * 400)
        assert result == 100  # 400 // 4

    @pytest.mark.asyncio
    async def test_uses_model_when_initialized(self):
        with patch("app.services.ai_engine.genai") as mock_genai:
            mock_model = MagicMock()
            mock_model.count_tokens_async = AsyncMock(return_value=MagicMock(total_tokens=42))
            mock_genai.configure.return_value = None
            mock_genai.GenerativeModel.return_value = mock_model
            mock_genai.GenerationConfig = MagicMock(return_value={})
            engine = AIEngine(api_key="test")
            engine.pro_model = mock_model
        result = await engine.count_tokens("some text here")
        assert result == 42

    @pytest.mark.asyncio
    async def test_fallback_on_model_exception(self):
        with patch("app.services.ai_engine.genai") as mock_genai:
            mock_model = MagicMock()
            mock_model.count_tokens_async = AsyncMock(side_effect=Exception("API down"))
            mock_genai.configure.return_value = None
            mock_genai.GenerativeModel.return_value = mock_model
            mock_genai.GenerationConfig = MagicMock(return_value={})
            engine = AIEngine(api_key="test")
            engine.pro_model = mock_model
        text = "x" * 800
        result = await engine.count_tokens(text)
        assert result == 200  # 800 // 4


# =============================================================================
# create_knowledge_cache
# =============================================================================


class TestCreateKnowledgeCache:
    @pytest.mark.asyncio
    async def test_returns_none_for_empty_files(self):
        with patch("app.services.ai_engine.genai"):
            engine = AIEngine(api_key="test")
        result = await engine.create_knowledge_cache([], cache_name="test_cache")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_cache_name_on_success(self):
        with (
            patch("app.services.ai_engine.genai") as mock_genai,
            patch("app.services.ai_engine.caching") as mock_caching,
            patch("app.services.ai_engine.settings") as mock_settings,
        ):
            mock_genai.configure.return_value = None
            mock_genai.GenerativeModel.return_value = MagicMock()
            mock_genai.GenerationConfig = MagicMock(return_value={})
            mock_settings.gemini_api_key = "key"
            mock_settings.gemini_model_pro = "gemini-1.5-pro"
            mock_cache = MagicMock()
            mock_cache.name = "cachedContents/abc123"
            mock_caching.CachedContent.create.return_value = mock_cache

            engine = AIEngine(api_key="test")
            files = [{"filename": "doc.pdf", "content": "text here"}]
            result = await engine.create_knowledge_cache(files, cache_name="kb_user1")

        assert result == "cachedContents/abc123"

    @pytest.mark.asyncio
    async def test_returns_none_on_exception(self):
        with (
            patch("app.services.ai_engine.genai") as mock_genai,
            patch("app.services.ai_engine.caching") as mock_caching,
        ):
            mock_genai.configure.return_value = None
            mock_genai.GenerativeModel.return_value = MagicMock()
            mock_genai.GenerationConfig = MagicMock(return_value={})
            mock_caching.CachedContent.create.side_effect = Exception("Quota exceeded")

            engine = AIEngine(api_key="test")
            files = [{"filename": "doc.pdf", "content": "text"}]
            result = await engine.create_knowledge_cache(files, cache_name="kb_fail")

        assert result is None


# =============================================================================
# get_cached_model
# =============================================================================


class TestGetCachedModel:
    def test_returns_none_on_cache_miss(self):
        with (
            patch("app.services.ai_engine.genai") as mock_genai,
            patch("app.services.ai_engine.caching") as mock_caching,
        ):
            mock_genai.configure.return_value = None
            mock_genai.GenerativeModel.return_value = MagicMock()
            mock_genai.GenerationConfig = MagicMock(return_value={})
            mock_caching.CachedContent.get.side_effect = Exception("Not found")

            engine = AIEngine(api_key="test")
            result = engine.get_cached_model("nonexistent/cache")

        assert result is None

    def test_returns_model_on_cache_hit(self):
        with (
            patch("app.services.ai_engine.genai") as mock_genai,
            patch("app.services.ai_engine.caching") as mock_caching,
        ):
            mock_genai.configure.return_value = None
            mock_model = MagicMock()
            mock_genai.GenerativeModel.return_value = mock_model
            mock_genai.GenerativeModel.from_cached_content = MagicMock(return_value=mock_model)
            mock_genai.GenerationConfig = MagicMock(return_value={})
            mock_cache = MagicMock()
            mock_caching.CachedContent.get.return_value = mock_cache

            engine = AIEngine(api_key="test")
            result = engine.get_cached_model("cachedContents/abc123")

        assert result is not None


# =============================================================================
# refresh_cache
# =============================================================================


class TestRefreshCache:
    @pytest.mark.asyncio
    async def test_returns_false_on_exception(self):
        with (
            patch("app.services.ai_engine.genai") as mock_genai,
            patch("app.services.ai_engine.caching") as mock_caching,
        ):
            mock_genai.configure.return_value = None
            mock_genai.GenerativeModel.return_value = MagicMock()
            mock_genai.GenerationConfig = MagicMock(return_value={})
            mock_caching.CachedContent.get.side_effect = Exception("cache gone")

            engine = AIEngine(api_key="test")
            result = await engine.refresh_cache("bad/cache")

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_true_on_success(self):
        with (
            patch("app.services.ai_engine.genai") as mock_genai,
            patch("app.services.ai_engine.caching") as mock_caching,
        ):
            mock_genai.configure.return_value = None
            mock_genai.GenerativeModel.return_value = MagicMock()
            mock_genai.GenerationConfig = MagicMock(return_value={})
            mock_cache = MagicMock()
            mock_cache.update.return_value = None
            mock_caching.CachedContent.get.return_value = mock_cache

            engine = AIEngine(api_key="test")
            result = await engine.refresh_cache("cachedContents/abc")

        assert result is True


# =============================================================================
# health_check
# =============================================================================


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_returns_false_when_not_initialized(self):
        with patch("app.services.ai_engine.settings") as mock_settings:
            mock_settings.gemini_api_key = None
            engine = AIEngine(api_key=None)
        result = await engine.health_check()
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_true_when_model_responds_ok(self):
        with patch("app.services.ai_engine.genai") as mock_genai:
            mock_flash = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "OK"
            mock_flash.generate_content_async = AsyncMock(return_value=mock_response)
            mock_genai.configure.return_value = None
            mock_genai.GenerativeModel.return_value = mock_flash
            mock_genai.GenerationConfig = MagicMock(return_value={})

            engine = AIEngine(api_key="test")
            engine.flash_model = mock_flash
            result = await engine.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_model_raises(self):
        with patch("app.services.ai_engine.genai") as mock_genai:
            mock_flash = MagicMock()
            mock_flash.generate_content_async = AsyncMock(side_effect=Exception("timeout"))
            mock_genai.configure.return_value = None
            mock_genai.GenerativeModel.return_value = mock_flash
            mock_genai.GenerationConfig = MagicMock(return_value={})

            engine = AIEngine(api_key="test")
            engine.flash_model = mock_flash
            result = await engine.health_check()

        assert result is False
