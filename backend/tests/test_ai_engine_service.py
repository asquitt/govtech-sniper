"""
Unit tests for ai_engine.py
============================
Tests for citation extraction/validation, data classes, initialization,
and token counting — all without hitting the Gemini API.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai_engine import (
    AIEngine,
    Citation,
    ExtractedRequirement,
    GeneratedDraft,
    get_ai_engine,
)

# =============================================================================
# Data Classes
# =============================================================================


class TestExtractedRequirement:
    def test_required_fields(self):
        req = ExtractedRequirement(
            id="REQ-001",
            section="L.5",
            text="The offeror shall provide...",
            requirement_type="Technical",
            importance="Mandatory",
        )
        assert req.id == "REQ-001"
        assert req.section == "L.5"
        assert req.requirement_type == "Technical"
        assert req.importance == "Mandatory"
        assert req.page_reference is None

    def test_optional_page_reference(self):
        req = ExtractedRequirement(
            id="REQ-002",
            section="M.1",
            text="Evaluated",
            requirement_type="Management",
            importance="Evaluated",
            page_reference=15,
        )
        assert req.page_reference == 15


class TestCitation:
    def test_citation_fields(self):
        c = Citation(
            source_file="resume.pdf",
            page_number=3,
            start_pos=10,
            end_pos=50,
            raw_text="[[Source: resume.pdf, Page 3]]",
        )
        assert c.source_file == "resume.pdf"
        assert c.page_number == 3
        assert c.start_pos == 10
        assert c.end_pos == 50

    def test_citation_no_page(self):
        c = Citation(
            source_file="doc.pdf",
            page_number=None,
            start_pos=0,
            end_pos=20,
            raw_text="[[Source: doc.pdf]]",
        )
        assert c.page_number is None


class TestGeneratedDraft:
    def test_draft_fields(self):
        draft = GeneratedDraft(
            raw_text="raw",
            clean_text="clean",
            citations=[],
            requirement_id="REQ-001",
            model="gemini-1.5-pro",
            tokens_used=100,
            generation_time=1.5,
        )
        assert draft.raw_text == "raw"
        assert draft.clean_text == "clean"
        assert draft.citations == []
        assert draft.requirement_id == "REQ-001"
        assert draft.tokens_used == 100
        assert draft.generation_time == 1.5


# =============================================================================
# AIEngine Initialization
# =============================================================================


class TestAIEngineInit:
    @patch("app.services.ai_engine.genai")
    def test_init_with_api_key(self, mock_genai):
        engine = AIEngine(api_key="test-key")
        assert engine._initialized is True
        mock_genai.configure.assert_called_once_with(api_key="test-key")

    @patch("app.services.ai_engine.settings")
    def test_init_without_api_key(self, mock_settings):
        mock_settings.gemini_api_key = ""
        engine = AIEngine(api_key=None)
        assert engine._initialized is False

    @patch("app.services.ai_engine.genai")
    def test_ensure_initialized_raises_when_not_initialized(self, mock_genai):
        mock_genai.configure = MagicMock()
        engine = AIEngine.__new__(AIEngine)
        engine._initialized = False
        with pytest.raises(RuntimeError, match="not initialized"):
            engine._ensure_initialized()


# =============================================================================
# Citation Extraction
# =============================================================================


class TestCitationExtraction:
    def _make_engine(self):
        engine = AIEngine.__new__(AIEngine)
        engine._initialized = False
        return engine

    def test_extract_single_citation_with_page(self):
        engine = self._make_engine()
        text = "We delivered 15 projects [[Source: Resume.pdf, Page 3]] on time."
        citations = engine._extract_citations(text)
        assert len(citations) == 1
        assert citations[0].source_file == "Resume.pdf"
        assert citations[0].page_number == 3

    def test_extract_citation_without_page(self):
        engine = self._make_engine()
        text = "Our team has expertise [[Source: capabilities.pdf]] in this area."
        citations = engine._extract_citations(text)
        assert len(citations) == 1
        assert citations[0].source_file == "capabilities.pdf"
        assert citations[0].page_number is None

    def test_extract_multiple_citations(self):
        engine = self._make_engine()
        text = "Claim one [[Source: A.pdf, Page 1]] and claim two [[Source: B.pdf, Page 5]]."
        citations = engine._extract_citations(text)
        assert len(citations) == 2
        assert citations[0].source_file == "A.pdf"
        assert citations[1].source_file == "B.pdf"
        assert citations[1].page_number == 5

    def test_extract_no_citations(self):
        engine = self._make_engine()
        text = "This text has no citations at all."
        citations = engine._extract_citations(text)
        assert citations == []

    def test_citation_positions_are_correct(self):
        engine = self._make_engine()
        text = "Start [[Source: doc.pdf, Page 2]] end"
        citations = engine._extract_citations(text)
        assert len(citations) == 1
        assert text[citations[0].start_pos : citations[0].end_pos] == "[[Source: doc.pdf, Page 2]]"

    def test_citation_case_insensitive_page(self):
        engine = self._make_engine()
        text = "text [[Source: file.pdf, page 10]] more"
        citations = engine._extract_citations(text)
        assert len(citations) == 1
        assert citations[0].page_number == 10

    def test_citation_with_spaces_in_filename(self):
        engine = self._make_engine()
        text = "text [[Source: my document.pdf, Page 7]] more"
        citations = engine._extract_citations(text)
        assert len(citations) == 1
        assert citations[0].source_file == "my document.pdf"


# =============================================================================
# Citation Validation
# =============================================================================


class TestCitationValidation:
    def _make_engine(self):
        engine = AIEngine.__new__(AIEngine)
        engine._initialized = False
        return engine

    @pytest.mark.asyncio
    async def test_validate_all_valid_citations(self):
        engine = self._make_engine()
        text = "Claim [[Source: Resume.pdf, Page 1]] and [[Source: PastPerf.pdf, Page 3]]"
        sources = ["Resume.pdf", "PastPerf.pdf"]
        valid, invalid = await engine.validate_citations(text, sources)
        assert len(valid) == 2
        assert len(invalid) == 0

    @pytest.mark.asyncio
    async def test_validate_with_invalid_citation(self):
        engine = self._make_engine()
        text = "Claim [[Source: Unknown.pdf, Page 1]]"
        sources = ["Resume.pdf"]
        valid, invalid = await engine.validate_citations(text, sources)
        assert len(valid) == 0
        assert len(invalid) == 1
        assert invalid[0].source_file == "Unknown.pdf"

    @pytest.mark.asyncio
    async def test_validate_case_insensitive(self):
        engine = self._make_engine()
        text = "Claim [[Source: resume.pdf, Page 1]]"
        sources = ["Resume.pdf"]
        valid, invalid = await engine.validate_citations(text, sources)
        assert len(valid) == 1
        assert len(invalid) == 0

    @pytest.mark.asyncio
    async def test_validate_mixed_results(self):
        engine = self._make_engine()
        text = (
            "A [[Source: good.pdf, Page 1]] "
            "B [[Source: bad.pdf, Page 2]] "
            "C [[Source: also_good.pdf, Page 3]]"
        )
        sources = ["good.pdf", "also_good.pdf"]
        valid, invalid = await engine.validate_citations(text, sources)
        assert len(valid) == 2
        assert len(invalid) == 1

    @pytest.mark.asyncio
    async def test_validate_no_citations(self):
        engine = self._make_engine()
        text = "No citations here."
        sources = ["file.pdf"]
        valid, invalid = await engine.validate_citations(text, sources)
        assert len(valid) == 0
        assert len(invalid) == 0


# =============================================================================
# Token Counting
# =============================================================================


class TestTokenCounting:
    @pytest.mark.asyncio
    async def test_count_tokens_uninitialized_uses_estimate(self):
        engine = AIEngine.__new__(AIEngine)
        engine._initialized = False
        count = await engine.count_tokens("Hello world this is a test")
        # Rough estimate: len // 4
        assert count == len("Hello world this is a test") // 4

    @pytest.mark.asyncio
    async def test_count_tokens_empty_string(self):
        engine = AIEngine.__new__(AIEngine)
        engine._initialized = False
        count = await engine.count_tokens("")
        assert count == 0


# =============================================================================
# Health Check
# =============================================================================


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_uninitialized(self):
        engine = AIEngine.__new__(AIEngine)
        engine._initialized = False
        result = await engine.health_check()
        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        engine = AIEngine.__new__(AIEngine)
        engine._initialized = True
        mock_response = MagicMock()
        mock_response.text = "OK"
        engine.flash_model = AsyncMock()
        engine.flash_model.generate_content_async = AsyncMock(return_value=mock_response)
        result = await engine.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        engine = AIEngine.__new__(AIEngine)
        engine._initialized = True
        engine.flash_model = AsyncMock()
        engine.flash_model.generate_content_async = AsyncMock(side_effect=RuntimeError("API error"))
        result = await engine.health_check()
        assert result is False


# =============================================================================
# Singleton
# =============================================================================


class TestGetAIEngine:
    def test_get_ai_engine_returns_instance(self):
        import app.services.ai_engine as mod

        mod._engine_instance = None
        with patch.object(AIEngine, "__init__", return_value=None):
            engine = get_ai_engine()
            assert engine is not None
            # Calling again returns same instance
            engine2 = get_ai_engine()
            assert engine is engine2
        mod._engine_instance = None  # cleanup
