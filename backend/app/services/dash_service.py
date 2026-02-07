"""
RFP Sniper - Dash Service
========================
Gemini-powered conversational AI assistant for GovCon workflows.
"""

import asyncio
from collections.abc import AsyncGenerator

import google.generativeai as genai
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.config import settings
from app.models.capture import CapturePlan
from app.models.knowledge_base import KnowledgeBaseDocument
from app.models.proposal import Proposal, ProposalSection
from app.models.rfp import RFP, ComplianceMatrix

logger = structlog.get_logger(__name__)

SYSTEM_PROMPT = """You are Dash, an AI assistant for government contracting professionals \
using GovTech Sniper.

Your role:
- Answer questions about opportunities, proposals, compliance, and capture strategy
- Help users understand RFP requirements and draft proposal content
- Provide actionable insights grounded in the user's data
- Be concise but thorough; use Markdown formatting

Rules:
- Only reference data provided in the context below. If information is not available, say so.
- When referencing specific documents, cite them by name.
- Never fabricate past performance, contract numbers, or award data.

{context}"""

MAX_HISTORY_MESSAGES = 20
MAX_RFP_TEXT_CHARS = 20_000
MAX_DOC_TEXT_CHARS = 10_000
MAX_KB_DOCS = 5


def _truncate(text: str, max_chars: int) -> str:
    if not text or len(text) <= max_chars:
        return text or ""
    return text[: max_chars - 3].rstrip() + "..."


async def _gather_context(
    db: AsyncSession,
    user_id: int,
    rfp_id: int | None,
) -> tuple[str, list[dict]]:
    """Gather user data context for the system prompt. Returns (context_text, citations)."""
    sections: list[str] = []
    citations: list[dict] = []

    # --- RFP context ---
    rfp: RFP | None = None
    if rfp_id is not None:
        result = await db.execute(select(RFP).where(RFP.id == rfp_id, RFP.user_id == user_id))
        rfp = result.scalar_one_or_none()

    if rfp:
        citations.append({"type": "rfp", "rfp_id": rfp.id, "title": rfp.title})
        parts = [f"## Active Opportunity\nTitle: {rfp.title}"]
        if rfp.agency:
            parts.append(f"Agency: {rfp.agency}")
        if rfp.solicitation_number:
            parts.append(f"Solicitation: {rfp.solicitation_number}")
        if rfp.response_deadline:
            parts.append(f"Deadline: {rfp.response_deadline.isoformat()}")
        if rfp.naics_code:
            parts.append(f"NAICS: {rfp.naics_code}")
        if rfp.set_aside:
            parts.append(f"Set-Aside: {rfp.set_aside}")
        summary = rfp.summary or rfp.description
        if summary:
            parts.append(f"Summary: {_truncate(summary, 2000)}")
        if rfp.full_text:
            parts.append(
                f"\nRFP Full Text (excerpt):\n{_truncate(rfp.full_text, MAX_RFP_TEXT_CHARS)}"
            )
        sections.append("\n".join(parts))

        # --- Compliance matrix ---
        matrix_result = await db.execute(
            select(ComplianceMatrix).where(ComplianceMatrix.rfp_id == rfp.id)
        )
        matrix = matrix_result.scalar_one_or_none()
        if matrix and matrix.requirements:
            reqs = matrix.requirements
            open_reqs = [r for r in reqs if not r.get("is_addressed")]
            lines = [f"\n## Compliance Matrix ({len(reqs)} requirements, {len(open_reqs)} open)"]
            for req in reqs[:15]:
                status = "OPEN" if not req.get("is_addressed") else "Addressed"
                lines.append(
                    f"- [{status}] {req.get('id')}: {_truncate(req.get('requirement_text', ''), 200)}"
                )
            if len(reqs) > 15:
                lines.append(f"... and {len(reqs) - 15} more requirements")
            sections.append("\n".join(lines))

        # --- Active proposal ---
        proposal_result = await db.execute(
            select(Proposal).where(Proposal.rfp_id == rfp.id, Proposal.user_id == user_id)
        )
        proposal = proposal_result.scalar_one_or_none()
        if proposal:
            sec_result = await db.execute(
                select(ProposalSection)
                .where(ProposalSection.proposal_id == proposal.id)
                .order_by(ProposalSection.display_order)
            )
            prop_sections = sec_result.scalars().all()
            if prop_sections:
                lines = [f"\n## Active Proposal (status: {proposal.status.value})"]
                for ps in prop_sections[:20]:
                    lines.append(f"- [{ps.status.value}] {ps.title}")
                sections.append("\n".join(lines))

        # --- Capture plan ---
        capture_result = await db.execute(
            select(CapturePlan).where(CapturePlan.rfp_id == rfp.id, CapturePlan.owner_id == user_id)
        )
        capture = capture_result.scalar_one_or_none()
        if capture:
            parts = [f"\n## Capture Plan (stage: {capture.stage.value})"]
            parts.append(f"Bid Decision: {capture.bid_decision.value}")
            if capture.win_probability is not None:
                parts.append(f"Win Probability: {capture.win_probability}%")
            if capture.notes:
                parts.append(f"Notes: {_truncate(capture.notes, 500)}")
            sections.append("\n".join(parts))

    # --- Knowledge base documents ---
    docs_result = await db.execute(
        select(KnowledgeBaseDocument)
        .where(KnowledgeBaseDocument.user_id == user_id)
        .order_by(KnowledgeBaseDocument.created_at.desc())
        .limit(MAX_KB_DOCS)
    )
    docs = docs_result.scalars().all()
    if docs:
        lines = ["\n## Knowledge Base Documents"]
        for doc in docs:
            citations.append(
                {
                    "type": "document",
                    "document_id": doc.id,
                    "title": doc.title,
                    "filename": doc.original_filename,
                }
            )
            lines.append(f"\n### {doc.original_filename}")
            if doc.full_text:
                lines.append(_truncate(doc.full_text, MAX_DOC_TEXT_CHARS))
            else:
                lines.append("(no text extracted)")
        sections.append("\n".join(lines))

    context_text = "\n".join(sections) if sections else "No user data available."
    return context_text, citations


def _build_gemini_history(conversation_history: list[dict] | None) -> list[dict]:
    """Convert stored messages to Gemini multi-turn format."""
    if not conversation_history:
        return []
    history = []
    for msg in conversation_history[-MAX_HISTORY_MESSAGES:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        # Gemini uses "model" not "assistant"
        gemini_role = "model" if role == "assistant" else "user"
        history.append({"role": gemini_role, "parts": [content]})
    return history


async def generate_dash_response(
    db: AsyncSession,
    *,
    user_id: int,
    question: str,
    rfp_id: int | None = None,
    conversation_history: list[dict] | None = None,
) -> tuple[str, list[dict]]:
    """Generate an AI-powered chat response grounded in user data."""
    context_text, citations = await _gather_context(db, user_id, rfp_id)

    if settings.mock_ai:
        answer = (
            f"**Mock Dash Response**\n\n"
            f"You asked: {question}\n\n"
            f"Context loaded: {'RFP and user data available' if rfp_id else 'No RFP selected'}\n\n"
            f"This is a mock response. Configure `GEMINI_API_KEY` for real AI."
        )
        return answer, citations

    if not settings.gemini_api_key:
        return "Gemini API is not configured. Set GEMINI_API_KEY to enable AI chat.", citations

    genai.configure(api_key=settings.gemini_api_key)
    system_instruction = SYSTEM_PROMPT.format(context=context_text)
    history = _build_gemini_history(conversation_history)

    try:
        model = genai.GenerativeModel(
            settings.gemini_model_flash,
            system_instruction=system_instruction,
            generation_config=genai.GenerationConfig(
                temperature=0.7,
                max_output_tokens=4096,
            ),
        )
        chat = model.start_chat(history=history)
        response = await chat.send_message_async(question)
        return response.text, citations
    except Exception as e:
        logger.error("Dash AI generation failed", error=str(e))
        return f"I encountered an error generating a response: {e}", citations


async def generate_dash_response_stream(
    db: AsyncSession,
    *,
    user_id: int,
    question: str,
    rfp_id: int | None = None,
    conversation_history: list[dict] | None = None,
) -> AsyncGenerator[str, None]:
    """Stream AI response chunks. Yields text chunks as they arrive."""
    context_text, _ = await _gather_context(db, user_id, rfp_id)

    if settings.mock_ai:
        mock_parts = [
            "**Mock Dash Response**\n\n",
            f"You asked: _{question}_\n\n",
            "This is a streaming mock response. ",
            "Configure `GEMINI_API_KEY` for real AI.",
        ]
        for part in mock_parts:
            yield part
            await asyncio.sleep(0.1)
        return

    if not settings.gemini_api_key:
        yield "Gemini API is not configured. Set GEMINI_API_KEY to enable AI chat."
        return

    genai.configure(api_key=settings.gemini_api_key)
    system_instruction = SYSTEM_PROMPT.format(context=context_text)
    history = _build_gemini_history(conversation_history)

    try:
        model = genai.GenerativeModel(
            settings.gemini_model_flash,
            system_instruction=system_instruction,
            generation_config=genai.GenerationConfig(
                temperature=0.7,
                max_output_tokens=4096,
            ),
        )
        chat = model.start_chat(history=history)
        response = await chat.send_message_async(question, stream=True)
        async for chunk in response:
            if chunk.text:
                yield chunk.text
    except Exception as e:
        logger.error("Dash AI streaming failed", error=str(e))
        yield f"\n\nI encountered an error: {e}"


async def get_context_citations(
    db: AsyncSession,
    *,
    user_id: int,
    rfp_id: int | None = None,
) -> list[dict]:
    """Get just the citations for the current context (used after streaming completes)."""
    _, citations = await _gather_context(db, user_id, rfp_id)
    return citations
