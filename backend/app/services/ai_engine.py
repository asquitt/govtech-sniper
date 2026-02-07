"""
RFP Sniper - AI Engine
=======================
Core AI functionality using Google Gemini 1.5 Pro.

Features:
- Context Caching: Upload Knowledge Base to Gemini's cache
- Matrix Extractor: Parse RFP PDFs into compliance requirements
- The Writer: Generate proposal sections with strict citation enforcement
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import google.generativeai as genai
import structlog
from google.generativeai import caching

from app.config import settings

logger = structlog.get_logger(__name__)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class ExtractedRequirement:
    """Single requirement extracted from RFP."""

    id: str
    section: str
    text: str
    requirement_type: str  # "Technical", "Management", "Past Performance", etc.
    importance: str  # "Mandatory", "Evaluated", "Optional"
    page_reference: int | None = None


@dataclass
class Citation:
    """Parsed citation from generated text."""

    source_file: str
    page_number: int | None
    start_pos: int
    end_pos: int
    raw_text: str


@dataclass
class GeneratedDraft:
    """Result of section generation."""

    raw_text: str
    clean_text: str
    citations: list[Citation]
    requirement_id: str
    model: str
    tokens_used: int
    generation_time: float


# =============================================================================
# AI Engine Class
# =============================================================================


class AIEngine:
    """
    Core AI engine for RFP analysis and proposal generation.

    Uses Google Gemini 1.5 Pro with:
    - 1M token context window for full document analysis
    - Context Caching API for Knowledge Base
    - Structured output for requirement extraction
    """

    # Citation pattern: [[Source: filename.pdf, Page XX]]
    CITATION_PATTERN = r"\[\[Source:\s*([^,\]]+)(?:,\s*[Pp]age\s*(\d+))?\]\]"

    # System prompts
    MATRIX_EXTRACTOR_PROMPT = """You are an expert government contracting analyst specializing in RFP compliance analysis.

Your task is to extract ALL compliance requirements from this RFP/Solicitation document.

For EACH requirement found, provide:
1. **Section**: The exact section reference (e.g., "L.5.2.1", "Section C.3")
2. **Text**: The complete requirement text
3. **Type**: One of: "Technical", "Management", "Past Performance", "Pricing", "Administrative", "Personnel", "Quality", "Security"
4. **Importance**: One of:
   - "Mandatory" (uses "shall", "must", "required" - non-compliance = disqualification)
   - "Evaluated" (scored in evaluation criteria)
   - "Optional" (nice to have, may enhance score)

EXTRACTION RULES:
- Extract EVERY requirement, not just obvious ones
- Pay special attention to Section L (Instructions) and Section M (Evaluation Criteria)
- Include format requirements (page limits, font sizes, etc.)
- Include deliverable requirements
- Include certification/attestation requirements
- If a requirement spans multiple sentences, include all related text

Return your response as a valid JSON object with this exact structure:
{
    "requirements": [
        {
            "id": "REQ-001",
            "section": "L.5.2.1",
            "text": "The offeror shall provide...",
            "type": "Technical",
            "importance": "Mandatory",
            "page_reference": 15
        }
    ],
    "document_summary": "Brief summary of the RFP scope and key objectives",
    "total_mandatory": 10,
    "total_evaluated": 5,
    "extraction_confidence": 0.95
}"""

    WRITER_SYSTEM_PROMPT = """You are an expert government proposal writer with decades of experience winning federal contracts.

CRITICAL CITATION REQUIREMENT:
Every factual claim, assertion of capability, or reference to past work MUST be cited using this EXACT format:
[[Source: Filename.pdf, Page X]]

CITATION RULES:
1. NEVER make a claim without a citation
2. If information comes from multiple pages, cite each one
3. If you cannot find a source for a claim, explicitly state: "[NEEDS SOURCE]"
4. Place citations IMMEDIATELY after the claim, not at the end of paragraphs

WRITING STYLE:
- Use active voice and concrete language
- Lead with the most compelling information
- Mirror the language used in the requirement
- Be specific with numbers, dates, and metrics
- Avoid filler words and empty claims

RESPONSE STRUCTURE:
1. Direct answer to the requirement (1-2 sentences)
2. Evidence with citations (bulk of response)
3. Summary/benefit statement

EXAMPLE OUTPUT:
"Our team has successfully delivered 15 Agile software development projects for federal agencies over the past 5 years [[Source: Past_Performance_Summary.pdf, Page 3]]. On the VA EHRM modernization program, we achieved a 99.7% on-time delivery rate across 47 sprints [[Source: VA_EHRM_Case_Study.pdf, Page 8]], demonstrating our proven ability to meet aggressive government timelines."

Remember: NO claim without a citation. The government evaluator must be able to verify every statement."""

    def __init__(self, api_key: str | None = None):
        """
        Initialize the AI Engine.

        Args:
            api_key: Gemini API key. Falls back to settings.
        """
        self.api_key = api_key or settings.gemini_api_key

        if not self.api_key:
            logger.warning("Gemini API key not configured")
            self._initialized = False
            return

        genai.configure(api_key=self.api_key)
        self._initialized = True

        # Initialize models
        self.pro_model = genai.GenerativeModel(
            settings.gemini_model_pro,
            generation_config=genai.GenerationConfig(
                temperature=0.2,
                max_output_tokens=8192,
            ),
        )

        self.flash_model = genai.GenerativeModel(
            settings.gemini_model_flash,
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                max_output_tokens=4096,
            ),
        )

        logger.info("AI Engine initialized", model_pro=settings.gemini_model_pro)

    def _ensure_initialized(self) -> None:
        """Raise error if not initialized."""
        if not self._initialized:
            raise RuntimeError("AI Engine not initialized. Check GEMINI_API_KEY.")

    # =========================================================================
    # Context Caching - Knowledge Base Upload
    # =========================================================================

    async def create_knowledge_cache(
        self,
        files: list[dict[str, Any]],
        cache_name: str,
        ttl_minutes: int = 60,
    ) -> str | None:
        """
        Upload user Knowledge Base files to Gemini's Context Caching API.

        This enables efficient reuse of context across multiple generation calls.

        Args:
            files: List of dicts with 'filename', 'content', and optional 'mime_type'
            cache_name: Unique identifier for this cache
            ttl_minutes: Cache time-to-live (default 60 minutes)

        Returns:
            Cache resource name for use in generation, or None if failed

        Example:
            cache = await engine.create_knowledge_cache([
                {"filename": "resume.pdf", "content": pdf_text},
                {"filename": "past_perf.pdf", "content": perf_text},
            ], cache_name="user_123_kb")
        """
        self._ensure_initialized()

        if not files:
            logger.warning("No files provided for caching")
            return None

        try:
            # Build combined content with clear document boundaries
            combined_content = []
            combined_content.append("=== KNOWLEDGE BASE DOCUMENTS ===\n")
            combined_content.append("Use these documents to cite sources in your responses.\n")
            combined_content.append("Always cite using: [[Source: Filename, Page X]]\n\n")

            for i, file_info in enumerate(files, 1):
                filename = file_info.get("filename", f"document_{i}.txt")
                content = file_info.get("content", "")

                combined_content.append(f"{'='*60}\n")
                combined_content.append(f"DOCUMENT {i}: {filename}\n")
                combined_content.append(f"{'='*60}\n\n")
                combined_content.append(content)
                combined_content.append("\n\n")

            full_content = "".join(combined_content)

            # Create the cache
            logger.info(
                "Creating Gemini context cache",
                cache_name=cache_name,
                file_count=len(files),
                content_length=len(full_content),
            )

            cache = caching.CachedContent.create(
                model=settings.gemini_model_pro,
                display_name=cache_name,
                contents=[full_content],
                ttl=timedelta(minutes=ttl_minutes),
                system_instruction=self.WRITER_SYSTEM_PROMPT,
            )

            logger.info(
                "Context cache created",
                cache_resource=cache.name,
                expires_at=(datetime.utcnow() + timedelta(minutes=ttl_minutes)).isoformat(),
            )

            return cache.name

        except Exception as e:
            logger.error(f"Failed to create context cache: {e}")
            return None

    def get_cached_model(self, cache_name: str) -> genai.GenerativeModel | None:
        """
        Get a GenerativeModel instance using cached context.

        Args:
            cache_name: The cache resource name from create_knowledge_cache

        Returns:
            GenerativeModel with cached context, or None if not found
        """
        self._ensure_initialized()

        try:
            cache = caching.CachedContent.get(cache_name)
            return genai.GenerativeModel.from_cached_content(cache)
        except Exception as e:
            logger.error(f"Failed to get cached model: {e}")
            return None

    async def refresh_cache(self, cache_name: str, ttl_minutes: int = 60) -> bool:
        """
        Extend the TTL of an existing cache.

        Args:
            cache_name: The cache resource name
            ttl_minutes: New TTL in minutes

        Returns:
            True if successful
        """
        try:
            cache = caching.CachedContent.get(cache_name)
            cache.update(ttl=timedelta(minutes=ttl_minutes))
            logger.info(f"Cache TTL extended: {cache_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to refresh cache: {e}")
            return False

    # =========================================================================
    # Matrix Extractor - RFP Requirement Extraction
    # =========================================================================

    async def extract_compliance_matrix(
        self,
        rfp_text: str,
        rfp_title: str | None = None,
    ) -> dict[str, Any]:
        """
        Extract compliance requirements from RFP text.

        Uses Gemini 1.5 Pro to analyze the full RFP document and
        extract structured requirements.

        Args:
            rfp_text: Full text content of the RFP
            rfp_title: Optional title for context

        Returns:
            Dictionary with requirements list and metadata
        """
        self._ensure_initialized()

        # Prepare the prompt
        context = f"RFP Title: {rfp_title}\n\n" if rfp_title else ""
        prompt = f"""{self.MATRIX_EXTRACTOR_PROMPT}

{context}RFP DOCUMENT:
{rfp_text[:500000]}

Extract all requirements and return as JSON."""

        logger.info(
            "Extracting compliance matrix",
            text_length=len(rfp_text),
            title=rfp_title,
        )

        start_time = datetime.utcnow()

        try:
            response = await self.pro_model.generate_content_async(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )

            elapsed = (datetime.utcnow() - start_time).total_seconds()

            # Parse response
            result = json.loads(response.text)

            # Convert to dataclass objects
            requirements = []
            for req_data in result.get("requirements", []):
                req = ExtractedRequirement(
                    id=req_data.get("id", f"REQ-{len(requirements)+1:03d}"),
                    section=req_data.get("section", "Unknown"),
                    text=req_data.get("text", ""),
                    requirement_type=req_data.get("type", "General"),
                    importance=req_data.get("importance", "Evaluated"),
                    page_reference=req_data.get("page_reference"),
                )
                requirements.append(req)

            logger.info(
                "Matrix extraction complete",
                requirements_found=len(requirements),
                mandatory_count=result.get("total_mandatory", 0),
                elapsed_seconds=elapsed,
            )

            return {
                "requirements": requirements,
                "summary": result.get("document_summary", ""),
                "total_mandatory": result.get("total_mandatory", 0),
                "total_evaluated": result.get("total_evaluated", 0),
                "confidence": result.get("extraction_confidence", 0.0),
                "raw_response": response.text,
                "extraction_time": elapsed,
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse extraction response: {e}")
            raise ValueError(f"Invalid JSON response from AI: {e}")
        except Exception as e:
            logger.error(f"Matrix extraction failed: {e}")
            raise

    # =========================================================================
    # The Writer - Proposal Section Generation
    # =========================================================================

    async def draft_section(
        self,
        requirement: ExtractedRequirement,
        cache_name: str | None = None,
        knowledge_base_text: str | None = None,
        additional_context: str | None = None,
        max_words: int = 500,
        tone: str = "professional",
    ) -> GeneratedDraft:
        """
        Generate a proposal section response to a requirement.

        Uses either cached context or inline knowledge base text.
        Enforces strict citation format: [[Source: Filename, Page X]]

        Args:
            requirement: The requirement to address
            cache_name: Gemini cache resource name (preferred)
            knowledge_base_text: Inline KB text (fallback if no cache)
            additional_context: Extra context to include
            max_words: Target word count
            tone: Writing tone

        Returns:
            GeneratedDraft with text and parsed citations
        """
        self._ensure_initialized()

        start_time = datetime.utcnow()

        # Get the model (cached or fresh)
        if cache_name:
            model = self.get_cached_model(cache_name)
            if not model:
                logger.warning("Cache not found, falling back to standard model")
                model = self.pro_model
        else:
            model = self.pro_model

        # Build the generation prompt
        prompt_parts = []

        if knowledge_base_text and not cache_name:
            prompt_parts.append("=== KNOWLEDGE BASE FOR CITATIONS ===")
            prompt_parts.append(knowledge_base_text[:200000])  # Limit size
            prompt_parts.append("\n" + "=" * 50 + "\n")

        prompt_parts.append(
            f"""
REQUIREMENT TO ADDRESS:
Section: {requirement.section}
Importance: {requirement.importance}
Type: {requirement.requirement_type}

Requirement Text:
{requirement.text}

INSTRUCTIONS:
1. Write a compelling response of approximately {max_words} words
2. Use a {tone} tone
3. EVERY factual claim MUST have a citation: [[Source: Filename, Page X]]
4. If you cannot find a source, write [NEEDS SOURCE]
5. Be specific with metrics, dates, and examples
"""
        )

        if additional_context:
            prompt_parts.append(f"\nADDITIONAL CONTEXT:\n{additional_context}")

        prompt_parts.append("\n\nWrite the proposal section now:")

        prompt = "\n".join(prompt_parts)

        try:
            response = await model.generate_content_async(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=max_words * 3,
                ),
            )

            elapsed = (datetime.utcnow() - start_time).total_seconds()
            raw_text = response.text

            # Parse citations
            citations = self._extract_citations(raw_text)

            # Create clean text (without citation markers)
            clean_text = re.sub(self.CITATION_PATTERN, "", raw_text)
            clean_text = re.sub(r"\s+", " ", clean_text).strip()

            # Get token count
            tokens = 0
            if hasattr(response, "usage_metadata"):
                tokens = response.usage_metadata.total_token_count

            logger.info(
                "Draft generated",
                requirement_id=requirement.id,
                word_count=len(clean_text.split()),
                citations=len(citations),
                elapsed=elapsed,
            )

            return GeneratedDraft(
                raw_text=raw_text,
                clean_text=clean_text,
                citations=citations,
                requirement_id=requirement.id,
                model=settings.gemini_model_pro,
                tokens_used=tokens,
                generation_time=elapsed,
            )

        except Exception as e:
            logger.error(f"Draft generation failed: {e}")
            raise

    def _extract_citations(self, text: str) -> list[Citation]:
        """
        Extract all citations from generated text.

        Args:
            text: Generated text with [[Source: ...]] markers

        Returns:
            List of Citation objects
        """
        citations = []

        for match in re.finditer(self.CITATION_PATTERN, text):
            source_file = match.group(1).strip()
            page_str = match.group(2)
            page_num = int(page_str) if page_str else None

            citations.append(
                Citation(
                    source_file=source_file,
                    page_number=page_num,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    raw_text=match.group(0),
                )
            )

        return citations

    # =========================================================================
    # Utility Methods
    # =========================================================================

    async def validate_citations(
        self,
        text: str,
        available_sources: list[str],
    ) -> tuple[list[Citation], list[Citation]]:
        """
        Validate citations against available sources.

        Args:
            text: Generated text with citations
            available_sources: List of valid source filenames

        Returns:
            Tuple of (valid_citations, invalid_citations)
        """
        citations = self._extract_citations(text)

        valid = []
        invalid = []

        # Normalize source names for comparison
        normalized_sources = {s.lower().strip(): s for s in available_sources}

        for citation in citations:
            normalized_cite = citation.source_file.lower().strip()

            # Check exact match
            if normalized_cite in normalized_sources or any(
                normalized_cite in src for src in normalized_sources
            ):
                valid.append(citation)
            else:
                invalid.append(citation)

        return valid, invalid

    async def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using Gemini's tokenizer.

        Args:
            text: Text to count

        Returns:
            Token count
        """
        if not self._initialized:
            return len(text) // 4  # Rough estimate

        try:
            result = await self.pro_model.count_tokens_async(text)
            return result.total_tokens
        except Exception:
            return len(text) // 4

    async def health_check(self) -> bool:
        """
        Verify Gemini API is accessible.

        Returns:
            True if healthy
        """
        if not self._initialized:
            return False

        try:
            response = await self.flash_model.generate_content_async(
                "Respond with only: OK",
                generation_config=genai.GenerationConfig(max_output_tokens=10),
            )
            return "ok" in response.text.lower()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


# =============================================================================
# Singleton Instance
# =============================================================================

_engine_instance: AIEngine | None = None


def get_ai_engine() -> AIEngine:
    """
    Get or create the AI Engine singleton.

    Returns:
        AIEngine instance
    """
    global _engine_instance

    if _engine_instance is None:
        _engine_instance = AIEngine()

    return _engine_instance
