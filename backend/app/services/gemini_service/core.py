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

from .prompts import (
    DEEP_READ_PROMPT,
    EXPAND_PROMPT,
    GENERATION_PROMPT,
    OUTLINE_PROMPT,
    REWRITE_PROMPT,
)

logger = structlog.get_logger(__name__)


class GeminiService:
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
    REWRITE_PROMPT = REWRITE_PROMPT
    EXPAND_PROMPT = EXPAND_PROMPT
    OUTLINE_PROMPT = OUTLINE_PROMPT

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

    def _extract_citations(self, text: str) -> list[Citation]:
        """
        Extract citations from generated text.

        Parses [[Source: filename.pdf, Page XX]] format.

        Args:
            text: Generated text with citation markers

        Returns:
            List of Citation objects
        """
        citations = []
        seen = set()

        for match in re.finditer(self.CITATION_PATTERN, text):
            source_file = match.group(1).strip()
            page_num = int(match.group(2)) if match.group(2) else None

            # Deduplicate
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
        prompt = self.REWRITE_PROMPT.format(
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
        prompt = self.EXPAND_PROMPT.format(
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

        prompt = self.OUTLINE_PROMPT.format(
            requirements_json=requirements_json[:50000],
            rfp_summary=rfp_summary[:5000],
        )

        import json

        response = await self.pro_model.generate_content_async(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.3,
                max_output_tokens=4096,
                response_mime_type="application/json",
            ),
        )
        return json.loads(response.text)

    # =========================================================================
    # Utility Methods
    # =========================================================================

    async def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using Gemini's tokenizer.

        Args:
            text: Text to count

        Returns:
            Token count
        """
        if not self.pro_model:
            # Rough estimate: ~4 chars per token
            return len(text) // 4

        try:
            result = await self.pro_model.count_tokens_async(text)
            return result.total_tokens
        except Exception:
            return len(text) // 4

    async def health_check(self) -> bool:
        """
        Verify Gemini API is accessible.

        Returns:
            True if API is healthy
        """
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
