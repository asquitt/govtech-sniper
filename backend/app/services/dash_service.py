"""
RFP Sniper - Dash Service
========================
Minimal context-aware assistant for Phase 0.
"""

from typing import Optional, Tuple, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.config import settings
from app.models.rfp import RFP
from app.models.knowledge_base import KnowledgeBaseDocument


async def generate_dash_response(
    session: AsyncSession,
    *,
    user_id: int,
    question: str,
    rfp_id: Optional[int] = None,
) -> Tuple[str, List[dict]]:
    """
    Generate a response with minimal grounding in internal data.
    Returns (content, citations).
    """
    citations: List[dict] = []
    summary_bits: List[str] = []

    rfp: Optional[RFP] = None
    if rfp_id is not None:
        result = await session.execute(
            select(RFP).where(RFP.id == rfp_id, RFP.user_id == user_id)
        )
        rfp = result.scalar_one_or_none()
        if rfp:
            summary_bits.append(f"Opportunity: {rfp.title}")
            if rfp.agency:
                summary_bits.append(f"Agency: {rfp.agency}")
            if rfp.response_deadline:
                summary_bits.append(f"Deadline: {rfp.response_deadline.isoformat()}")

    docs_result = await session.execute(
        select(KnowledgeBaseDocument)
        .where(KnowledgeBaseDocument.user_id == user_id)
        .order_by(KnowledgeBaseDocument.created_at.desc())
        .limit(3)
    )
    docs = docs_result.scalars().all()

    for doc in docs:
        citations.append({
            "document_id": doc.id,
            "title": doc.title,
            "filename": doc.original_filename,
        })

    if settings.mock_ai:
        response = " ".join(summary_bits) if summary_bits else "No opportunity context found."
        if docs:
            response += f" Referenced {len(docs)} knowledge base document(s)."
        response += f" Question: {question}"
        return response, citations

    # If not mocked, return a safe fallback for now.
    response = "I can help summarize opportunities and reference your knowledge base."
    if summary_bits:
        response += " " + " ".join(summary_bits)
    if question:
        response += f" Question: {question}"
    return response, citations
