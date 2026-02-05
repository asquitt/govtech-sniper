"""
RFP Sniper - Dash Service
========================
Context-aware assistant with lightweight tool dispatch for Phase 4.
"""

from typing import Optional, Tuple, List, Dict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.config import settings
from app.models.rfp import RFP, ComplianceMatrix
from app.models.knowledge_base import KnowledgeBaseDocument
from app.models.award import AwardRecord
from app.models.contact import OpportunityContact


def _detect_intent(question: str) -> str:
    text = (question or "").lower()
    if any(keyword in text for keyword in ["summarize", "summary", "overview"]):
        return "summary"
    if any(keyword in text for keyword in ["compliance", "gap", "gaps", "missing"]):
        return "compliance_gap"
    if any(keyword in text for keyword in ["capability", "capabilities", "capability statement"]):
        return "capability_statement"
    if any(keyword in text for keyword in ["competitor", "competition", "award", "awardee", "incumbent", "competitive"]):
        return "competitive_intel"
    return "general"


def _truncate(text: str, max_chars: int = 400) -> str:
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def _build_rfp_context(rfp: Optional[RFP]) -> str:
    if not rfp:
        return "No opportunity context found."

    parts = [f"Opportunity: {rfp.title}"]
    if rfp.agency:
        parts.append(f"Agency: {rfp.agency}")
    if rfp.response_deadline:
        parts.append(f"Deadline: {rfp.response_deadline.isoformat()}")
    if rfp.naics_code:
        parts.append(f"NAICS: {rfp.naics_code}")
    if rfp.set_aside:
        parts.append(f"Set-Aside: {rfp.set_aside}")
    return " | ".join(parts)


def _build_doc_citations(docs: List[KnowledgeBaseDocument]) -> List[dict]:
    citations: List[dict] = []
    for doc in docs:
        citations.append({
            "type": "document",
            "document_id": doc.id,
            "title": doc.title,
            "filename": doc.original_filename,
        })
    return citations


def _summarize_compliance(matrix: ComplianceMatrix) -> Tuple[str, List[dict]]:
    open_requirements = [req for req in matrix.requirements if not req.get("is_addressed")]
    citations = []
    top_items = open_requirements[:5]
    for req in top_items:
        citations.append({
            "type": "requirement",
            "requirement_id": req.get("id"),
            "section": req.get("section"),
        })
    if not open_requirements:
        return "All compliance requirements are marked as addressed.", citations

    summary_lines = [
        f"Compliance gaps: {len(open_requirements)} requirement(s) still open.",
        "Top gaps:",
    ]
    for req in top_items:
        summary_lines.append(f"- {req.get('id')}: {req.get('requirement_text')}")
    return "\n".join(summary_lines), citations


def _summarize_awards(awards: List[AwardRecord]) -> Tuple[str, List[dict]]:
    if not awards:
        return "No award intelligence records found yet.", []

    top_awards = sorted(
        awards,
        key=lambda award: award.award_amount or 0,
        reverse=True,
    )[:3]
    citations: List[dict] = []
    lines = [f"Award records found: {len(awards)}."]
    for award in top_awards:
        citations.append({
            "type": "award",
            "award_id": award.id,
            "awardee": award.awardee_name,
        })
        amount = f"${award.award_amount:,}" if award.award_amount else "Amount TBD"
        vehicle = award.contract_vehicle or "Vehicle unknown"
        lines.append(f"- {award.awardee_name} · {amount} · {vehicle}")
    return "\n".join(lines), citations


def _summarize_contacts(contacts: List[OpportunityContact]) -> Tuple[str, List[dict]]:
    if not contacts:
        return "No opportunity contacts recorded.", []
    top_contacts = contacts[:3]
    citations: List[dict] = []
    lines = [f"Contacts recorded: {len(contacts)}."]
    for contact in top_contacts:
        citations.append({
            "type": "contact",
            "contact_id": contact.id,
            "name": contact.name,
        })
        role = contact.role or "Role unknown"
        org = contact.organization or "Org unknown"
        lines.append(f"- {contact.name} · {role} · {org}")
    return "\n".join(lines), citations


async def generate_dash_response(
    session: AsyncSession,
    *,
    user_id: int,
    question: str,
    rfp_id: Optional[int] = None,
) -> Tuple[str, List[dict]]:
    """
    Generate a response grounded in internal data.
    Returns (content, citations).
    """
    citations: List[dict] = []

    rfp: Optional[RFP] = None
    if rfp_id is not None:
        result = await session.execute(
            select(RFP).where(RFP.id == rfp_id, RFP.user_id == user_id)
        )
        rfp = result.scalar_one_or_none()
        if rfp:
            citations.append({
                "type": "rfp",
                "rfp_id": rfp.id,
                "title": rfp.title,
            })

    docs_result = await session.execute(
        select(KnowledgeBaseDocument)
        .where(KnowledgeBaseDocument.user_id == user_id)
        .order_by(KnowledgeBaseDocument.created_at.desc())
        .limit(3)
    )
    docs = docs_result.scalars().all()
    citations.extend(_build_doc_citations(docs))

    intent = _detect_intent(question)
    context = _build_rfp_context(rfp)

    if intent == "summary":
        if not rfp:
            answer = "Select an opportunity to summarize."
        else:
            base_text = rfp.summary or rfp.description or "No description available."
            answer = f"{context}\nSummary: {_truncate(base_text)}"
    elif intent == "compliance_gap":
        if not rfp:
            answer = "Select an opportunity to analyze compliance gaps."
        else:
            matrix_result = await session.execute(
                select(ComplianceMatrix).where(ComplianceMatrix.rfp_id == rfp.id)
            )
            matrix = matrix_result.scalar_one_or_none()
            if not matrix:
                answer = f"{context}\nNo compliance matrix found for this opportunity."
            else:
                gap_summary, gap_citations = _summarize_compliance(matrix)
                citations.extend(gap_citations)
                answer = f"{context}\n{gap_summary}"
    elif intent == "capability_statement":
        if not docs:
            answer = "Upload capability statements or past performance documents to draft a statement."
        else:
            doc_titles = ", ".join([doc.title for doc in docs])
            answer = (
                f"Draft capability statement for {context}: "
                f"Our team delivers mission-ready solutions backed by {doc_titles}. "
                "We have proven experience supporting federal programs with secure, compliant delivery."
            )
    elif intent == "competitive_intel":
        awards: List[AwardRecord] = []
        contacts: List[OpportunityContact] = []
        if rfp:
            awards_result = await session.execute(
                select(AwardRecord).where(
                    AwardRecord.user_id == user_id,
                    AwardRecord.rfp_id == rfp.id,
                )
            )
            awards = awards_result.scalars().all()
            contacts_result = await session.execute(
                select(OpportunityContact).where(
                    OpportunityContact.user_id == user_id,
                    OpportunityContact.rfp_id == rfp.id,
                )
            )
            contacts = contacts_result.scalars().all()
        else:
            awards_result = await session.execute(
                select(AwardRecord)
                .where(AwardRecord.user_id == user_id)
                .order_by(AwardRecord.created_at.desc())
                .limit(5)
            )
            awards = awards_result.scalars().all()

        award_summary, award_citations = _summarize_awards(awards)
        contact_summary, contact_citations = _summarize_contacts(contacts)
        citations.extend(award_citations)
        citations.extend(contact_citations)

        base_context = context if rfp else "Competitive intel summary (all awards)"
        answer = f"{base_context}\n{award_summary}\n{contact_summary}"
    else:
        answer = (
            f"{context}\nI can help with summaries, compliance gap analysis, or capability statements. "
            f"Ask a specific question and I will ground the response in your data."
        )

    if settings.mock_ai:
        answer = f"{answer} (mock)"

    return answer, citations
