"""
RFP Sniper - Gemini AI Service
===============================
Core AI integration using Google Gemini 1.5 Pro.

Key Features:
- Context Caching for Knowledge Base documents
- Deep Read analysis for compliance extraction
- RAG-style generation with citation tracking
"""

import re
from datetime import datetime, timedelta
from typing import Any

import google.generativeai as genai
import structlog
from google.generativeai import caching

try:
    from google.api_core.exceptions import ResourceExhausted as GeminiResourceExhausted
except Exception:  # pragma: no cover - dependency shape can vary by runtime
    GeminiResourceExhausted = None

from app.config import settings
from app.models.knowledge_base import KnowledgeBaseDocument
from app.models.proposal import Citation, GeneratedContent
from app.models.rfp import ComplianceRequirement, ImportanceLevel

from .generation import GeminiGenerationMixin
from .prompts import (
    DEEP_READ_PROMPT,
    GENERATION_PROMPT,
)

logger = structlog.get_logger(__name__)


class GeminiService(GeminiGenerationMixin):
    """
    Service for Google Gemini AI operations.

    Implements:
    - Deep Read: Extract compliance matrix from RFP text
    - Context Caching: Upload Knowledge Base to Gemini's cache
    - Proposal Generation: RAG with citations
    """

    # Citation pattern: [[Source: filename.pdf, Page XX]]
    CITATION_PATTERN = r"\[\[Source:\s*([^,\]]+)(?:,\s*Page\s*(\d+))?\]\]"
    RETRY_IN_PATTERN = re.compile(r"retry in\s+([0-9]+(?:\.[0-9]+)?)s", re.IGNORECASE)
    RETRY_DELAY_PATTERN = re.compile(
        r"retry_delay\s*\{\s*seconds:\s*(\d+)",
        re.IGNORECASE | re.DOTALL,
    )
    DAILY_QUOTA_PATTERN = re.compile(r"per[_\s-]?day", re.IGNORECASE)
    _quota_circuit_open_until: datetime | None = None

    # Prompt templates (imported from .prompts)
    DEEP_READ_PROMPT = DEEP_READ_PROMPT
    GENERATION_PROMPT = GENERATION_PROMPT

    def __init__(self, api_key: str | None = None):
        """
        Initialize Gemini service.

        Args:
            api_key: Gemini API key. Falls back to settings.
        """
        self.api_key = api_key or settings.gemini_api_key

        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.pro_model_name = self._resolve_model_name(
                settings.gemini_model_pro,
                fallback_keywords=["gemini", "pro"],
            )
            self.flash_model_name = self._resolve_model_name(
                settings.gemini_model_flash,
                fallback_keywords=["gemini", "flash"],
            )
            self.pro_model = genai.GenerativeModel(self.pro_model_name)
            self.flash_model = genai.GenerativeModel(self.flash_model_name)
        else:
            self.pro_model_name = settings.gemini_model_pro
            self.flash_model_name = settings.gemini_model_flash
            self.pro_model = None
            self.flash_model = None
            logger.warning("Gemini API key not configured")

    def _resolve_model_name(self, preferred: str, fallback_keywords: list[str]) -> str:
        """
        Resolve a usable model name from the API, falling back to a best match.
        """
        try:
            models = genai.list_models()
        except Exception as e:
            logger.warning("Failed to list Gemini models; using configured name", error=str(e))
            return preferred

        def supports_generate(m) -> bool:
            methods = getattr(m, "supported_generation_methods", None) or []
            return "generateContent" in methods

        candidates = [m for m in models if supports_generate(m)]

        # Exact or suffix match for preferred
        for m in candidates:
            if m.name == preferred or m.name.endswith(preferred):
                return m.name

        # Keyword-based fallback
        for m in candidates:
            name = m.name.lower()
            if all(keyword in name for keyword in fallback_keywords):
                return m.name

        return preferred

    def _is_quota_error(self, exc: Exception) -> bool:
        if GeminiResourceExhausted is not None and isinstance(exc, GeminiResourceExhausted):
            return True
        lowered = str(exc).lower()
        return "quota exceeded" in lowered or "resourceexhausted" in lowered

    def _extract_retry_after_seconds(self, exc: Exception) -> int | None:
        message = str(exc)
        retry_match = self.RETRY_IN_PATTERN.search(message)
        if retry_match:
            return max(1, int(float(retry_match.group(1))))

        retry_delay_match = self.RETRY_DELAY_PATTERN.search(message)
        if retry_delay_match:
            return max(1, int(retry_delay_match.group(1)))

        return None

    def _get_remaining_quota_circuit_seconds(self) -> int | None:
        blocked_until = self.__class__._quota_circuit_open_until
        if not blocked_until:
            return None
        remaining = int((blocked_until - datetime.utcnow()).total_seconds())
        if remaining <= 0:
            self.__class__._quota_circuit_open_until = None
            return None
        return remaining

    def _open_quota_circuit(
        self,
        *,
        retry_after_seconds: int | None,
        error_message: str,
    ) -> int:
        cooldown = retry_after_seconds or settings.gemini_rate_limit_cooldown_seconds
        if self.DAILY_QUOTA_PATTERN.search(error_message):
            cooldown = max(cooldown, settings.gemini_rate_limit_daily_cooldown_seconds)
        cooldown = max(1, min(cooldown, settings.gemini_rate_limit_max_seconds))
        self.__class__._quota_circuit_open_until = datetime.utcnow() + timedelta(seconds=cooldown)
        logger.warning("Gemini quota circuit opened", open_seconds=cooldown)
        return cooldown

    def _ensure_quota_available(self) -> None:
        remaining = self._get_remaining_quota_circuit_seconds()
        if remaining:
            raise RuntimeError(
                f"Gemini API rate limit reached. Retry in about {remaining} seconds."
            )

    def _configured_fallback_model_names(self) -> list[str]:
        configured = [
            model.strip() for model in settings.gemini_fallback_models.split(",") if model.strip()
        ]
        return configured

    def _build_model_candidates(
        self,
        *,
        primary_model: genai.GenerativeModel | None,
        primary_model_name: str | None,
    ) -> list[tuple[str, genai.GenerativeModel]]:
        candidates: list[tuple[str, genai.GenerativeModel]] = []
        seen_names: set[str] = set()

        if primary_model is not None:
            label = primary_model_name or "primary"
            candidates.append((label, primary_model))
            if primary_model_name:
                seen_names.add(primary_model_name)

        if self.flash_model is not None and self.flash_model_name not in seen_names:
            candidates.append((self.flash_model_name, self.flash_model))
            seen_names.add(self.flash_model_name)

        if not self.api_key:
            return candidates

        for model_name in self._configured_fallback_model_names():
            if model_name in seen_names:
                continue
            try:
                candidates.append((model_name, genai.GenerativeModel(model_name)))
                seen_names.add(model_name)
            except Exception as e:
                logger.warning(
                    "Failed to initialize fallback model",
                    model=model_name,
                    error=str(e),
                )

        return candidates

    async def _generate_with_fallback(
        self,
        *,
        prompt: str,
        generation_config: genai.GenerationConfig,
        primary_model: genai.GenerativeModel | None,
        primary_model_name: str | None,
    ) -> tuple[Any, str]:
        self._ensure_quota_available()

        candidates = self._build_model_candidates(
            primary_model=primary_model,
            primary_model_name=primary_model_name,
        )
        if not candidates:
            raise ValueError("Gemini model not available")

        max_retry_after = 0
        last_quota_error: Exception | None = None
        last_error: Exception | None = None

        for model_name, model in candidates:
            try:
                response = await model.generate_content_async(
                    prompt,
                    generation_config=generation_config,
                )
                if model_name != (primary_model_name or "primary"):
                    logger.info("Gemini fallback model used", model=model_name)
                return response, model_name
            except Exception as exc:
                last_error = exc
                if self._is_quota_error(exc):
                    last_quota_error = exc
                    retry_after = self._extract_retry_after_seconds(exc) or 0
                    max_retry_after = max(max_retry_after, retry_after)
                    logger.warning(
                        "Gemini model quota-limited; trying fallback if available",
                        model=model_name,
                        retry_after=retry_after or None,
                    )
                    continue
                raise

        if last_quota_error is not None:
            message = str(last_quota_error)
            cooldown = self._open_quota_circuit(
                retry_after_seconds=max_retry_after or None,
                error_message=message,
            )
            if "limit: 0" in message.lower():
                raise RuntimeError(
                    "Gemini quota is unavailable for the configured model. "
                    "Enable billing or configure GEMINI_FALLBACK_MODELS. "
                    f"Retry in about {cooldown} seconds."
                )
            raise RuntimeError(f"Gemini API rate limit reached. Retry in about {cooldown} seconds.")

        if last_error is not None:
            raise last_error
        raise RuntimeError("Gemini generation failed unexpectedly.")

    # =========================================================================
    # Deep Read: Compliance Matrix Extraction
    # =========================================================================

    async def deep_read(
        self,
        rfp_text: str,
        max_tokens: int = 8192,
    ) -> dict[str, Any]:
        """
        Perform Deep Read analysis on RFP text.

        Uses Gemini 1.5 Pro's massive context window to analyze
        the full document and extract compliance requirements.

        Args:
            rfp_text: Full text of the RFP document
            max_tokens: Maximum response tokens

        Returns:
            Dictionary with requirements, summary, and metadata
        """
        if settings.mock_ai:
            requirement = ComplianceRequirement(
                id="REQ-001",
                section="Section L.1",
                source_section="Section L",
                requirement_text="The contractor shall provide the required services.",
                importance=ImportanceLevel.MANDATORY,
                category="Technical",
                page_reference=1,
                keywords=["contractor", "services"],
            )
            return {
                "requirements": [requirement],
                "summary": "Mock analysis summary",
                "confidence": 0.5,
                "raw_response": "{}",
            }

        if not self.pro_model:
            raise ValueError("Gemini API not configured")

        # Prepare the prompt
        prompt = self.DEEP_READ_PROMPT.format(rfp_text=rfp_text[:100000])  # Limit to ~100K chars

        logger.info("Starting Deep Read analysis", text_length=len(rfp_text))
        start_time = datetime.utcnow()

        try:
            response, model_used = await self._generate_with_fallback(
                prompt=prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=max_tokens,
                    response_mime_type="application/json",
                ),
                primary_model=self.pro_model,
                primary_model_name=self.pro_model_name,
            )

            import json

            result = json.loads(response.text)

            # Parse requirements into domain models
            requirements = []
            for req_data in result.get("requirements", []):
                try:
                    importance = ImportanceLevel(
                        req_data.get("importance", "informational").lower()
                    )
                except ValueError:
                    importance = ImportanceLevel.INFORMATIONAL

                req = ComplianceRequirement(
                    id=req_data.get("id", f"REQ-{len(requirements) + 1:03d}"),
                    section=req_data.get("section", "Unknown"),
                    source_section=req_data.get("source_section"),
                    requirement_text=req_data.get("requirement_text", ""),
                    importance=importance,
                    category=req_data.get("category"),
                    page_reference=req_data.get("page_reference"),
                    keywords=req_data.get("keywords", []),
                    confidence=req_data.get("confidence", 0.0),
                )
                requirements.append(req)

            elapsed = (datetime.utcnow() - start_time).total_seconds()
            logger.info(
                "Deep Read complete",
                requirements_found=len(requirements),
                elapsed_seconds=elapsed,
                model_used=model_used,
            )

            return {
                "requirements": requirements,
                "summary": result.get("summary", ""),
                "confidence": result.get("confidence", 0.0),
                "raw_response": response.text,
            }

        except Exception as e:
            logger.error(f"Deep Read failed: {e}")
            raise

    # =========================================================================
    # Context Caching: Knowledge Base Upload
    # =========================================================================

    async def create_context_cache(
        self,
        documents: list[KnowledgeBaseDocument],
        cache_name: str,
        ttl_hours: int = 24,
    ) -> str | None:
        """
        Upload documents to Gemini's Context Caching API.

        This allows referencing large document sets without
        re-uploading them with each request.

        Args:
            documents: List of knowledge base documents
            cache_name: Unique name for this cache
            ttl_hours: Cache time-to-live in hours

        Returns:
            Cache resource name, or None if failed
        """
        if not self.api_key:
            logger.error("Cannot create cache: API key not configured")
            return None

        try:
            # Combine all document texts with clear separators
            combined_text = ""
            for doc in documents:
                if doc.full_text:
                    combined_text += f"\n\n{'=' * 50}\n"
                    combined_text += f"DOCUMENT: {doc.original_filename}\n"
                    combined_text += f"TYPE: {doc.document_type.value}\n"
                    combined_text += f"{'=' * 50}\n\n"
                    combined_text += doc.full_text

            if not combined_text:
                logger.warning("No document content to cache")
                return None

            # Create the cache
            cache = caching.CachedContent.create(
                model=settings.gemini_model_pro,
                display_name=cache_name,
                contents=[combined_text],
                ttl=timedelta(hours=ttl_hours),
                system_instruction="""You are a proposal writing assistant.
When generating text, you MUST cite your sources using this exact format:
[[Source: filename.pdf, Page XX]]

Every factual claim must have a citation. If you cannot find a source, say so explicitly.""",
            )

            logger.info(
                "Context cache created",
                cache_name=cache.name,
                document_count=len(documents),
                ttl_hours=ttl_hours,
            )

            return cache.name

        except Exception as e:
            logger.error(f"Failed to create context cache: {e}")
            return None

    def get_cached_model(self, cache_name: str) -> genai.GenerativeModel | None:
        """
        Get a model instance using a cached context.

        Args:
            cache_name: The cache resource name

        Returns:
            GenerativeModel with cached context, or None
        """
        try:
            cache = caching.CachedContent.get(cache_name)
            return genai.GenerativeModel.from_cached_content(cache)
        except Exception as e:
            logger.error(f"Failed to get cached model: {e}")
            return None

    # =========================================================================
    # Proposal Generation with Citations
    # =========================================================================

    async def generate_section(
        self,
        requirement_text: str,
        section: str,
        category: str,
        cache_name: str | None = None,
        documents_text: str | None = None,
        max_words: int = 500,
        tone: str = "professional",
    ) -> GeneratedContent:
        """
        Generate proposal section with citations.

        Uses either cached context or inline document text
        to generate a response with source citations.

        Args:
            requirement_text: The requirement to address
            section: Section number/name
            category: Requirement category
            cache_name: Cached content name (preferred)
            documents_text: Fallback inline document text
            max_words: Target word count
            tone: Writing tone (professional/technical/executive)

        Returns:
            GeneratedContent with raw text, clean text, and citations
        """
        if settings.mock_ai:
            citation_text = "[[Source: Mock_Document.pdf, Page 1]]"
            raw_text = f"This is a mock response generated for testing purposes. {citation_text}"
            return GeneratedContent(
                raw_text=raw_text,
                clean_text="This is a mock response generated for testing purposes.",
                citations=[
                    Citation(source_file="Mock_Document.pdf", page_number=1, confidence=1.0)
                ],
                model_used="mock",
                tokens_used=0,
                generation_time_seconds=0.0,
            )

        start_time = datetime.utcnow()

        # Get the model (cached or fresh)
        if cache_name:
            model = self.get_cached_model(cache_name)
            if not model:
                logger.warning("Cache not found, using fresh model")
                model = self.pro_model
        else:
            model = self.pro_model

        if not model:
            raise ValueError("Gemini model not available")

        # Build prompt
        prompt = self.GENERATION_PROMPT.format(
            requirement_text=requirement_text,
            section=section,
            category=category or "General",
            tone=tone,
            max_words=max_words,
        )

        # Add documents text if not using cache
        if documents_text and not cache_name:
            prompt = f"KNOWLEDGE BASE DOCUMENTS:\n{documents_text}\n\n{prompt}"

        try:
            response, model_used = await self._generate_with_fallback(
                prompt=prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=max_words * 3,  # Rough token estimate
                ),
                primary_model=model,
                primary_model_name=self.pro_model_name if model is self.pro_model else "cached",
            )

            raw_text = response.text
            elapsed = (datetime.utcnow() - start_time).total_seconds()

            # Parse citations
            citations = self._extract_citations(raw_text)

            # Create clean text (remove citation markers)
            clean_text = re.sub(self.CITATION_PATTERN, "", raw_text).strip()
            clean_text = re.sub(r"\s+", " ", clean_text)  # Normalize whitespace

            # Get token usage
            tokens_used = (
                response.usage_metadata.total_token_count
                if hasattr(response, "usage_metadata")
                else 0
            )

            logger.info(
                "Section generated",
                section=section,
                word_count=len(clean_text.split()),
                citations_found=len(citations),
                elapsed_seconds=elapsed,
            )

            return GeneratedContent(
                raw_text=raw_text,
                clean_text=clean_text,
                citations=citations,
                model_used=model_used,
                tokens_used=tokens_used,
                generation_time_seconds=elapsed,
            )

        except Exception as e:
            logger.error(f"Section generation failed: {e}")
            raise

    # Rewrite, expand, outline, citations, count_tokens, health_check
    # are inherited from GeminiGenerationMixin (see generation.py)
