"""
RFP Sniper - Generation Tasks
==============================
Celery tasks for proposal section generation.
"""

import asyncio
from datetime import datetime
from typing import Optional, List
import structlog

from app.tasks.celery_app import celery_app
from app.services.gemini_service import GeminiService
from app.database import get_celery_session_context
from app.models.rfp import RFP, ComplianceMatrix
from app.models.proposal import Proposal, ProposalSection, SectionStatus
from app.models.knowledge_base import KnowledgeBaseDocument, ProcessingStatus
from app.models.proposal_focus_document import ProposalFocusDocument

logger = structlog.get_logger(__name__)


def run_async(coro):
    """Helper to run async code in Celery tasks."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    bind=True,
    name="app.tasks.generation_tasks.generate_proposal_section",
    max_retries=2,
    default_retry_delay=60,
)
def generate_proposal_section(
    self,
    section_id: int,
    user_id: int,
    max_words: int = 500,
    tone: str = "professional",
    additional_context: Optional[str] = None,
) -> dict:
    """
    Generate content for a proposal section using RAG.
    
    Uses Gemini 1.5 Pro with Knowledge Base context.
    
    Args:
        section_id: ID of the proposal section to generate
        user_id: User ID for Knowledge Base lookup
        max_words: Target word count
        tone: Writing tone
        additional_context: Extra context to include
        
    Returns:
        Generation results
    """
    task_id = self.request.id
    logger.info(
        "Starting section generation",
        task_id=task_id,
        section_id=section_id,
    )
    
    async def _generate():
        gemini_service = GeminiService()
        
        async with get_celery_session_context() as session:
            from sqlmodel import select
            
            # Get the section
            section_result = await session.execute(
                select(ProposalSection).where(ProposalSection.id == section_id)
            )
            section = section_result.scalar_one_or_none()
            
            if not section:
                return {
                    "task_id": task_id,
                    "status": "error",
                    "error": f"Section {section_id} not found",
                }
            
            # Update status
            section.status = SectionStatus.GENERATING
            await session.commit()
            
            # Check for focus documents first
            focus_result = await session.execute(
                select(ProposalFocusDocument).where(
                    ProposalFocusDocument.proposal_id == section.proposal_id
                ).order_by(ProposalFocusDocument.priority_order)
            )
            focus_docs = focus_result.scalars().all()

            if focus_docs:
                # Use only focus documents
                focus_doc_ids = [fd.document_id for fd in focus_docs]
                docs_result = await session.execute(
                    select(KnowledgeBaseDocument).where(
                        KnowledgeBaseDocument.id.in_(focus_doc_ids),
                        KnowledgeBaseDocument.processing_status == ProcessingStatus.READY,
                    )
                )
            else:
                # Fall back to all user documents
                docs_result = await session.execute(
                    select(KnowledgeBaseDocument).where(
                        KnowledgeBaseDocument.user_id == user_id,
                        KnowledgeBaseDocument.processing_status == ProcessingStatus.READY,
                    )
                )
            documents = docs_result.scalars().all()
            
            # Check for cached context or build inline
            cache_name = None
            documents_text = None
            
            # Look for a valid cache
            for doc in documents:
                if doc.gemini_cache_name and doc.gemini_cache_expires_at:
                    if doc.gemini_cache_expires_at > datetime.utcnow():
                        cache_name = doc.gemini_cache_name
                        break
            
            # If no cache, build inline text
            if not cache_name and documents:
                documents_text = "\n\n".join([
                    f"=== DOCUMENT: {doc.original_filename} ===\n{doc.full_text or ''}"
                    for doc in documents
                    if doc.full_text
                ])
            
            # Get requirement details
            requirement_text = section.requirement_text or section.title

            # Include writing plan if user provided one
            if section.writing_plan:
                requirement_text += f"\n\nWRITING PLAN:\n{section.writing_plan}"

            # Add additional context if provided
            if additional_context:
                requirement_text += f"\n\nAdditional Context: {additional_context}"
            
            try:
                # Generate content
                generated = await gemini_service.generate_section(
                    requirement_text=requirement_text,
                    section=section.section_number,
                    category=None,  # Could extract from compliance matrix
                    cache_name=cache_name,
                    documents_text=documents_text,
                    max_words=max_words,
                    tone=tone,
                )
                
                # Update section
                section.set_generated_content(generated)
                
                # Update proposal completion count
                proposal_result = await session.execute(
                    select(Proposal).where(Proposal.id == section.proposal_id)
                )
                proposal = proposal_result.scalar_one_or_none()
                
                if proposal:
                    # Count completed sections
                    completed_result = await session.execute(
                        select(ProposalSection).where(
                            ProposalSection.proposal_id == proposal.id,
                            ProposalSection.status.in_([
                                SectionStatus.GENERATED,
                                SectionStatus.APPROVED,
                            ])
                        )
                    )
                    completed_sections = len(completed_result.scalars().all())
                    proposal.completed_sections = completed_sections
                
                # Update citation counts on documents
                for citation in generated.citations:
                    for doc in documents:
                        if doc.original_filename == citation.source_file:
                            doc.times_cited += 1
                            doc.last_cited_at = datetime.utcnow()
                            break
                
                await session.commit()
                
                logger.info(
                    "Section generated",
                    section_id=section_id,
                    word_count=len(generated.clean_text.split()),
                    citations=len(generated.citations),
                )
                
                return {
                    "task_id": task_id,
                    "status": "completed",
                    "section_id": section_id,
                    "word_count": len(generated.clean_text.split()),
                    "citations_count": len(generated.citations),
                    "tokens_used": generated.tokens_used,
                    "generation_time": generated.generation_time_seconds,
                }
                
            except Exception as e:
                logger.error(f"Generation failed: {e}", section_id=section_id)
                section.status = SectionStatus.PENDING
                await session.commit()
                raise self.retry(exc=e)
    
    return run_async(_generate())


@celery_app.task(
    bind=True,
    name="app.tasks.generation_tasks.generate_all_sections",
)
def generate_all_sections(
    self,
    proposal_id: int,
    user_id: int,
    max_words_per_section: int = 500,
    tone: str = "professional",
) -> dict:
    """
    Generate all pending sections for a proposal.
    
    Args:
        proposal_id: ID of the proposal
        user_id: User ID
        max_words_per_section: Word limit per section
        tone: Writing tone
        
    Returns:
        Summary of generation tasks queued
    """
    task_id = self.request.id
    logger.info("Generating all sections", task_id=task_id, proposal_id=proposal_id)
    
    async def _queue_all():
        async with get_celery_session_context() as session:
            from sqlmodel import select
            
            # Get pending sections
            result = await session.execute(
                select(ProposalSection).where(
                    ProposalSection.proposal_id == proposal_id,
                    ProposalSection.status == SectionStatus.PENDING,
                ).order_by(ProposalSection.display_order)
            )
            sections = result.scalars().all()
            
            queued_tasks = []
            for section in sections:
                # Queue individual generation tasks
                task = generate_proposal_section.delay(
                    section_id=section.id,
                    user_id=user_id,
                    max_words=max_words_per_section,
                    tone=tone,
                )
                queued_tasks.append({
                    "section_id": section.id,
                    "task_id": task.id,
                })
            
            return {
                "parent_task_id": task_id,
                "status": "queued",
                "sections_queued": len(queued_tasks),
                "tasks": queued_tasks,
            }
    
    return run_async(_queue_all())


@celery_app.task(
    name="app.tasks.generation_tasks.refresh_context_cache",
)
def refresh_context_cache(
    user_id: int,
    ttl_hours: int = 24,
) -> dict:
    """
    Refresh/create Gemini context cache for user's knowledge base.
    
    Args:
        user_id: User ID
        ttl_hours: Cache time-to-live
        
    Returns:
        Cache creation result
    """
    logger.info("Refreshing context cache", user_id=user_id)
    
    async def _refresh():
        gemini_service = GeminiService()
        
        async with get_celery_session_context() as session:
            from sqlmodel import select
            
            # Get user's ready documents
            result = await session.execute(
                select(KnowledgeBaseDocument).where(
                    KnowledgeBaseDocument.user_id == user_id,
                    KnowledgeBaseDocument.processing_status == ProcessingStatus.READY,
                )
            )
            documents = list(result.scalars().all())
            
            if not documents:
                return {"status": "skipped", "reason": "No ready documents"}
            
            # Create cache
            cache_name = await gemini_service.create_context_cache(
                documents=documents,
                cache_name=f"user_{user_id}_kb",
                ttl_hours=ttl_hours,
            )
            
            if cache_name:
                # Update documents with cache info
                expires_at = datetime.utcnow()
                from datetime import timedelta
                expires_at += timedelta(hours=ttl_hours)
                
                for doc in documents:
                    doc.gemini_cache_name = cache_name
                    doc.gemini_cache_expires_at = expires_at
                
                await session.commit()
                
                return {
                    "status": "created",
                    "cache_name": cache_name,
                    "documents_cached": len(documents),
                    "expires_at": expires_at.isoformat(),
                }
            else:
                return {"status": "failed", "reason": "Cache creation failed"}
    
    return run_async(_refresh())
