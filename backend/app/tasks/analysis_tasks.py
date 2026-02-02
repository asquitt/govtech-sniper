"""
RFP Sniper - Analysis Tasks
============================
Celery tasks for RFP analysis using Gemini AI.
"""

import asyncio
from datetime import datetime
from typing import Optional
import structlog

from celery import shared_task

from app.tasks.celery_app import celery_app
from app.services.gemini_service import GeminiService
from app.services.filters import KillerFilterService
from app.database import get_celery_session_context
from app.models.rfp import RFP, RFPStatus, ComplianceMatrix
from app.models.user import UserProfile

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
    name="app.tasks.analysis_tasks.analyze_rfp",
    max_retries=2,
    default_retry_delay=120,
)
def analyze_rfp(
    self,
    rfp_id: int,
    force_reanalyze: bool = False,
) -> dict:
    """
    Celery task to perform Deep Read analysis on an RFP.
    
    Uses Gemini 1.5 Pro to extract the compliance matrix.
    
    Args:
        rfp_id: ID of the RFP to analyze
        force_reanalyze: If True, re-analyze even if already done
        
    Returns:
        Analysis results summary
    """
    task_id = self.request.id
    logger.info("Starting RFP analysis", task_id=task_id, rfp_id=rfp_id)
    
    async def _analyze():
        gemini_service = GeminiService()
        
        async with get_celery_session_context() as session:
            from sqlmodel import select
            
            # Get the RFP
            result = await session.execute(
                select(RFP).where(RFP.id == rfp_id)
            )
            rfp = result.scalar_one_or_none()
            
            if not rfp:
                return {
                    "task_id": task_id,
                    "status": "error",
                    "error": f"RFP {rfp_id} not found",
                }
            
            # Check if already analyzed
            if rfp.status == RFPStatus.ANALYZED and not force_reanalyze:
                return {
                    "task_id": task_id,
                    "status": "skipped",
                    "message": "RFP already analyzed",
                    "rfp_id": rfp_id,
                }
            
            # Update status
            rfp.status = RFPStatus.ANALYZING
            await session.commit()
            
            # Get text to analyze
            text_to_analyze = rfp.full_text or rfp.description
            if not text_to_analyze:
                rfp.status = RFPStatus.NEW
                await session.commit()
                return {
                    "task_id": task_id,
                    "status": "error",
                    "error": "No text content to analyze",
                }
            
            try:
                # Run Deep Read
                analysis = await gemini_service.deep_read(text_to_analyze)
                
                # Check for existing compliance matrix
                matrix_result = await session.execute(
                    select(ComplianceMatrix).where(ComplianceMatrix.rfp_id == rfp_id)
                )
                compliance_matrix = matrix_result.scalar_one_or_none()
                
                if compliance_matrix:
                    # Update existing
                    compliance_matrix.requirements = [
                        req.model_dump() for req in analysis["requirements"]
                    ]
                    compliance_matrix.total_requirements = len(analysis["requirements"])
                    compliance_matrix.mandatory_count = sum(
                        1 for req in analysis["requirements"]
                        if req.importance.value == "mandatory"
                    )
                    compliance_matrix.extraction_confidence = analysis.get("confidence", 0)
                    compliance_matrix.raw_ai_response = analysis.get("raw_response")
                    compliance_matrix.updated_at = datetime.utcnow()
                else:
                    # Create new
                    compliance_matrix = ComplianceMatrix(
                        rfp_id=rfp_id,
                        requirements=[
                            req.model_dump() for req in analysis["requirements"]
                        ],
                        total_requirements=len(analysis["requirements"]),
                        mandatory_count=sum(
                            1 for req in analysis["requirements"]
                            if req.importance.value == "mandatory"
                        ),
                        extraction_confidence=analysis.get("confidence", 0),
                        raw_ai_response=analysis.get("raw_response"),
                    )
                    session.add(compliance_matrix)
                
                # Update RFP
                rfp.status = RFPStatus.ANALYZED
                rfp.summary = analysis.get("summary")
                rfp.analyzed_at = datetime.utcnow()
                
                await session.commit()
                
                logger.info(
                    "RFP analysis complete",
                    rfp_id=rfp_id,
                    requirements_found=len(analysis["requirements"]),
                )
                
                return {
                    "task_id": task_id,
                    "status": "completed",
                    "rfp_id": rfp_id,
                    "requirements_found": len(analysis["requirements"]),
                    "mandatory_count": compliance_matrix.mandatory_count,
                    "confidence": analysis.get("confidence", 0),
                }
                
            except Exception as e:
                logger.error(f"Analysis failed: {e}", rfp_id=rfp_id)
                rfp.status = RFPStatus.NEW
                await session.commit()
                raise self.retry(exc=e)
    
    return run_async(_analyze())


@celery_app.task(
    bind=True,
    name="app.tasks.analysis_tasks.run_killer_filter",
)
def run_killer_filter(
    self,
    rfp_id: int,
    user_id: int,
) -> dict:
    """
    Run the Killer Filter on a specific RFP.
    
    Args:
        rfp_id: ID of the RFP to filter
        user_id: ID of the user (for profile lookup)
        
    Returns:
        Filter results
    """
    task_id = self.request.id
    logger.info("Running Killer Filter", task_id=task_id, rfp_id=rfp_id)
    
    async def _filter():
        filter_service = KillerFilterService()
        
        async with get_celery_session_context() as session:
            from sqlmodel import select
            
            # Get RFP and user profile
            rfp_result = await session.execute(
                select(RFP).where(RFP.id == rfp_id)
            )
            rfp = rfp_result.scalar_one_or_none()
            
            if not rfp:
                return {"status": "error", "error": "RFP not found"}
            
            profile_result = await session.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
            profile = profile_result.scalar_one_or_none()
            
            if not profile:
                return {"status": "error", "error": "User profile not found"}
            
            # Run filter
            result = await filter_service.filter_rfp(rfp, profile)
            
            # Update RFP
            rfp.is_qualified = result.is_qualified
            rfp.qualification_reason = result.reason
            rfp.qualification_score = result.confidence * 100
            
            await session.commit()
            
            return {
                "task_id": task_id,
                "status": "completed",
                "rfp_id": rfp_id,
                "is_qualified": result.is_qualified,
                "reason": result.reason,
                "confidence": result.confidence,
                "disqualifying_factors": result.disqualifying_factors,
                "matching_factors": result.matching_factors,
            }
    
    return run_async(_filter())


@celery_app.task(name="app.tasks.analysis_tasks.cleanup_expired_caches")
def cleanup_expired_caches():
    """
    Clean up expired Gemini context caches.
    Runs via Celery Beat schedule.
    """
    logger.info("Cleaning up expired context caches")
    
    async def _cleanup():
        async with get_session_context() as session:
            from sqlmodel import select
            from app.models.knowledge_base import KnowledgeBaseDocument
            
            # Find documents with expired caches
            now = datetime.utcnow()
            result = await session.execute(
                select(KnowledgeBaseDocument).where(
                    KnowledgeBaseDocument.gemini_cache_expires_at < now,
                    KnowledgeBaseDocument.gemini_cache_name.isnot(None),
                )
            )
            expired_docs = result.scalars().all()
            
            for doc in expired_docs:
                doc.gemini_cache_name = None
                doc.gemini_cache_expires_at = None
                logger.info(f"Cleared expired cache for document {doc.id}")
            
            if expired_docs:
                await session.commit()
            
            return {"cleaned": len(expired_docs)}
    
    return run_async(_cleanup())
