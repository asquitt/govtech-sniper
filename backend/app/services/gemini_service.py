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
from typing import List, Optional, Dict, Any
import structlog

import google.generativeai as genai
from google.generativeai import caching

from app.config import settings
from app.models.rfp import ComplianceRequirement, ImportanceLevel
from app.models.proposal import Citation, GeneratedContent
from app.models.knowledge_base import KnowledgeBaseDocument

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
    CITATION_PATTERN = r'\[\[Source:\s*([^,\]]+)(?:,\s*Page\s*(\d+))?\]\]'
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini service.
        
        Args:
            api_key: Gemini API key. Falls back to settings.
        """
        self.api_key = api_key or settings.gemini_api_key
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
            pro_name = self._resolve_model_name(
                settings.gemini_model_pro,
                fallback_keywords=["gemini", "pro"],
            )
            flash_name = self._resolve_model_name(
                settings.gemini_model_flash,
                fallback_keywords=["gemini", "flash"],
            )
            self.pro_model = genai.GenerativeModel(pro_name)
            self.flash_model = genai.GenerativeModel(flash_name)
        else:
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
    
    # =========================================================================
    # Deep Read: Compliance Matrix Extraction
    # =========================================================================
    
    DEEP_READ_PROMPT = """You are an expert government proposal analyst. Extract ALL compliance requirements from this RFP by systematically analyzing every section.

IMPORTANT: Government RFPs scatter requirements across multiple sections. You MUST analyze ALL of the following if present:

1. **Section C / SOW / PWS**: Technical requirements, deliverables, performance standards, SLAs, acceptance criteria
2. **Section H**: Key personnel, security clearances, OCI provisions, insurance/bonding/licensing
3. **Section L**: Proposal format, page limits, volume structure, submission instructions, certifications
4. **Section M**: Evaluation factors/subfactors, scoring methodology, relative importance
5. **Other sections** (J, F, etc.): CDRLs, data items, delivery schedules, reporting requirements

For EACH requirement provide:
1. Unique ID (e.g., REQ-001)
2. Granular source reference (e.g., "Section L.3.2 - Proposal Format")
3. source_section: one of "Section C", "Section H", "Section L", "Section M", "PWS", "SOW", "Section J", "Section F", "Other"
4. Exact requirement text
5. Importance: MANDATORY, EVALUATED, OPTIONAL, or INFORMATIONAL
6. Category: Technical, Management, Past Performance, Pricing, Administrative, Personnel, Quality, or Security
7. Page reference if available
8. Key terms/keywords

CRITICAL:
- MANDATORY requirements use "shall", "must", "required" language
- Look for evaluation criteria in Section M for scored items
- Include ALL deliverables, certifications, and format requirements
- Do NOT skip Section C/PWS requirements — these are often the most critical

RFP DOCUMENT:
{rfp_text}

Respond with ONLY valid JSON in this format:
{{
    "requirements": [
        {{
            "id": "REQ-001",
            "section": "Section C.3.1 - Software Development",
            "source_section": "Section C",
            "requirement_text": "The contractor shall provide...",
            "importance": "mandatory",
            "category": "Technical",
            "page_reference": 12,
            "keywords": ["contractor", "provide", "deliverable"]
        }}
    ],
    "summary": "Brief summary of the RFP scope",
    "total_mandatory": 5,
    "confidence": 0.95
}}"""

    async def deep_read(
        self,
        rfp_text: str,
        max_tokens: int = 8192,
    ) -> Dict[str, Any]:
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
            response = await self.pro_model.generate_content_async(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=max_tokens,
                    response_mime_type="application/json",
                ),
            )
            
            import json
            result = json.loads(response.text)
            
            # Parse requirements into domain models
            requirements = []
            for req_data in result.get("requirements", []):
                try:
                    importance = ImportanceLevel(req_data.get("importance", "informational").lower())
                except ValueError:
                    importance = ImportanceLevel.INFORMATIONAL
                
                req = ComplianceRequirement(
                    id=req_data.get("id", f"REQ-{len(requirements)+1:03d}"),
                    section=req_data.get("section", "Unknown"),
                    source_section=req_data.get("source_section"),
                    requirement_text=req_data.get("requirement_text", ""),
                    importance=importance,
                    category=req_data.get("category"),
                    page_reference=req_data.get("page_reference"),
                    keywords=req_data.get("keywords", []),
                )
                requirements.append(req)
            
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            logger.info(
                "Deep Read complete",
                requirements_found=len(requirements),
                elapsed_seconds=elapsed,
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
        documents: List[KnowledgeBaseDocument],
        cache_name: str,
        ttl_hours: int = 24,
    ) -> Optional[str]:
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
                    combined_text += f"\n\n{'='*50}\n"
                    combined_text += f"DOCUMENT: {doc.original_filename}\n"
                    combined_text += f"TYPE: {doc.document_type.value}\n"
                    combined_text += f"{'='*50}\n\n"
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
    
    def get_cached_model(self, cache_name: str) -> Optional[genai.GenerativeModel]:
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
    
    GENERATION_PROMPT = """You are an expert government proposal writer. Write a response to address this requirement.

REQUIREMENT:
{requirement_text}

SECTION: {section}
CATEGORY: {category}

INSTRUCTIONS:
1. Write a compelling, compliant response
2. EVERY factual claim MUST cite the source document
3. Use this EXACT citation format: [[Source: filename.pdf, Page XX]]
4. Be specific about experience, metrics, and qualifications
5. Match the required tone: {tone}
6. Target word count: approximately {max_words} words
7. If a WRITING PLAN is included above, follow its guidance on key points, themes, strengths to highlight, and tone preferences

If the Knowledge Base doesn't contain relevant information, state that clearly.

Write the response now:"""

    async def generate_section(
        self,
        requirement_text: str,
        section: str,
        category: str,
        cache_name: Optional[str] = None,
        documents_text: Optional[str] = None,
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
            raw_text = (
                "This is a mock response generated for testing purposes. "
                f"{citation_text}"
            )
            return GeneratedContent(
                raw_text=raw_text,
                clean_text="This is a mock response generated for testing purposes.",
                citations=[Citation(source_file="Mock_Document.pdf", page_number=1, confidence=1.0)],
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
            response = await model.generate_content_async(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=max_words * 3,  # Rough token estimate
                ),
            )
            
            raw_text = response.text
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            
            # Parse citations
            citations = self._extract_citations(raw_text)
            
            # Create clean text (remove citation markers)
            clean_text = re.sub(self.CITATION_PATTERN, '', raw_text).strip()
            clean_text = re.sub(r'\s+', ' ', clean_text)  # Normalize whitespace
            
            # Get token usage
            tokens_used = response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else 0
            
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
                model_used=settings.gemini_model_pro,
                tokens_used=tokens_used,
                generation_time_seconds=elapsed,
            )
            
        except Exception as e:
            logger.error(f"Section generation failed: {e}")
            raise
    
    def _extract_citations(self, text: str) -> List[Citation]:
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
            
            citations.append(Citation(
                source_file=source_file,
                page_number=page_num,
                confidence=1.0,
            ))
        
        return citations
    
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
