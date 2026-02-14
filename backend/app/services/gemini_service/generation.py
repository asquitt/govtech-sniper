"""
Gemini generation mixin — rewrite, expand, outline, utilities.
"""

import json
import re
from datetime import datetime
from typing import TYPE_CHECKING

import google.generativeai as genai
import structlog

from app.models.proposal import Citation, GeneratedContent

from . import settings
from .prompts import EXPAND_PROMPT, OUTLINE_PROMPT, REWRITE_PROMPT

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)


class GeminiGenerationMixin:
    """Methods for rewrite, expand, outline, citations, and health check."""

    # These are set on GeminiService — declared here for type hints only
    CITATION_PATTERN: str
    pro_model: object
    pro_model_name: str
    flash_model: object
    REWRITE_PROMPT: str
    EXPAND_PROMPT: str
    OUTLINE_PROMPT: str

    async def _generate_with_fallback(self, **kwargs):  # type: ignore[override]
        raise NotImplementedError  # overridden by core.GeminiService

    def _extract_citations(self, text: str) -> list[Citation]:
        """
        Extract citations from generated text.

        Parses [[Source: filename.pdf, Page XX]] format.
        """
        citations = []
        seen: set[tuple[str, int | None]] = set()

        for match in re.finditer(self.CITATION_PATTERN, text):
            source_file = match.group(1).strip()
            page_num = int(match.group(2)) if match.group(2) else None

            key = (source_file, page_num)
            if key in seen:
                continue
            seen.add(key)

            citations.append(
                Citation(
                    source_file=source_file,
                    page_number=page_num,
                    confidence=1.0,
                )
            )

        return citations

    # =========================================================================
    # Rewrite & Expand
    # =========================================================================

    async def rewrite_section(
        self,
        content: str,
        requirement_text: str,
        tone: str = "professional",
        instructions: str | None = None,
        documents_text: str | None = None,
    ) -> GeneratedContent:
        """Rewrite existing section content with a new tone or instructions."""
        if settings.mock_ai:
            return GeneratedContent(
                raw_text=f"[Rewritten] {content}",
                clean_text=f"[Rewritten] {re.sub(self.CITATION_PATTERN, '', content).strip()}",
                citations=self._extract_citations(content),
                model_used="mock",
                tokens_used=0,
                generation_time_seconds=0.0,
            )

        if not self.pro_model:
            raise ValueError("Gemini model not available")

        start_time = datetime.utcnow()

        custom = f"5. Additional instructions: {instructions}" if instructions else ""
        prompt = REWRITE_PROMPT.format(
            content=content,
            requirement_text=requirement_text or "N/A",
            tone=tone,
            custom_instructions=custom,
        )

        if documents_text:
            prompt = f"KNOWLEDGE BASE DOCUMENTS:\n{documents_text}\n\n{prompt}"

        response, model_used = await self._generate_with_fallback(
            prompt=prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.7,
                max_output_tokens=len(content.split()) * 4,
            ),
            primary_model=self.pro_model,
            primary_model_name=self.pro_model_name,
        )

        raw_text = response.text
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        citations = self._extract_citations(raw_text)
        clean_text = re.sub(self.CITATION_PATTERN, "", raw_text).strip()
        clean_text = re.sub(r"\s+", " ", clean_text)
        tokens_used = (
            response.usage_metadata.total_token_count if hasattr(response, "usage_metadata") else 0
        )

        return GeneratedContent(
            raw_text=raw_text,
            clean_text=clean_text,
            citations=citations,
            model_used=model_used,
            tokens_used=tokens_used,
            generation_time_seconds=elapsed,
        )

    async def expand_section(
        self,
        content: str,
        requirement_text: str,
        target_words: int = 800,
        focus_area: str | None = None,
        documents_text: str | None = None,
    ) -> GeneratedContent:
        """Expand existing section content with more detail."""
        if settings.mock_ai:
            expanded = f"{content}\n\n[Expanded with additional detail on the requirement.]"
            return GeneratedContent(
                raw_text=expanded,
                clean_text=re.sub(self.CITATION_PATTERN, "", expanded).strip(),
                citations=self._extract_citations(content),
                model_used="mock",
                tokens_used=0,
                generation_time_seconds=0.0,
            )

        if not self.pro_model:
            raise ValueError("Gemini model not available")

        start_time = datetime.utcnow()

        focus = f"6. Focus especially on: {focus_area}" if focus_area else ""
        prompt = EXPAND_PROMPT.format(
            content=content,
            requirement_text=requirement_text or "N/A",
            target_words=target_words,
            focus_instructions=focus,
        )

        if documents_text:
            prompt = f"KNOWLEDGE BASE DOCUMENTS:\n{documents_text}\n\n{prompt}"

        response, model_used = await self._generate_with_fallback(
            prompt=prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.7,
                max_output_tokens=target_words * 3,
            ),
            primary_model=self.pro_model,
            primary_model_name=self.pro_model_name,
        )

        raw_text = response.text
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        citations = self._extract_citations(raw_text)
        clean_text = re.sub(self.CITATION_PATTERN, "", raw_text).strip()
        clean_text = re.sub(r"\s+", " ", clean_text)
        tokens_used = (
            response.usage_metadata.total_token_count if hasattr(response, "usage_metadata") else 0
        )

        return GeneratedContent(
            raw_text=raw_text,
            clean_text=clean_text,
            citations=citations,
            model_used=model_used,
            tokens_used=tokens_used,
            generation_time_seconds=elapsed,
        )

    # =========================================================================
    # Outline Generation
    # =========================================================================

    async def generate_outline(
        self,
        requirements_json: str,
        rfp_summary: str,
    ) -> dict:
        """Generate a structured proposal outline from compliance requirements."""
        if settings.mock_ai:
            return {
                "sections": [
                    {
                        "title": "Executive Summary",
                        "description": "Overview of the proposal approach.",
                        "mapped_requirement_ids": [],
                        "estimated_pages": 2,
                        "children": [],
                    },
                    {
                        "title": "Technical Approach",
                        "description": "Detailed technical solution.",
                        "mapped_requirement_ids": ["REQ-001"],
                        "estimated_pages": 8,
                        "children": [],
                    },
                ]
            }

        if not self.pro_model:
            raise ValueError("Gemini API not configured")

        prompt = OUTLINE_PROMPT.format(
            requirements_json=requirements_json[:50000],
            rfp_summary=rfp_summary[:5000],
        )

        response, _model_used = await self._generate_with_fallback(
            prompt=prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.3,
                max_output_tokens=4096,
                response_mime_type="application/json",
            ),
            primary_model=self.pro_model,
            primary_model_name=self.pro_model_name,
        )
        return json.loads(response.text)

    # =========================================================================
    # Utility Methods
    # =========================================================================

    async def count_tokens(self, text: str) -> int:
        """Count tokens in text using Gemini's tokenizer."""
        if not self.pro_model:
            return len(text) // 4

        try:
            result = await self.pro_model.count_tokens_async(text)
            return result.total_tokens
        except Exception:
            return len(text) // 4

    async def health_check(self) -> bool:
        """Verify Gemini API is accessible."""
        if settings.mock_ai:
            return True
        if not self.flash_model:
            return False

        try:
            response = await self.flash_model.generate_content_async(
                "Say 'OK' if you're working.",
                generation_config=genai.GenerationConfig(max_output_tokens=10),
            )
            return "ok" in response.text.lower()
        except Exception as e:
            logger.error(f"Gemini health check failed: {e}")
            return False
