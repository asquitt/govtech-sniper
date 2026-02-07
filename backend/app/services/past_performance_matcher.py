"""Past performance matching and narrative generation."""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.knowledge_base import DocumentType, KnowledgeBaseDocument
from app.models.rfp import RFP


class PastPerformanceMatch:
    """Scored match between a past performance doc and an RFP."""

    def __init__(self, document_id: int, title: str, score: float, matching_criteria: list[str]):
        self.document_id = document_id
        self.title = title
        self.score = score
        self.matching_criteria = matching_criteria


async def match_past_performances(
    session: AsyncSession,
    rfp_id: int,
    user_id: int,
) -> list[PastPerformanceMatch]:
    """Score relevance of past performance docs against RFP requirements."""
    rfp_result = await session.execute(select(RFP).where(RFP.id == rfp_id, RFP.user_id == user_id))
    rfp = rfp_result.scalar_one_or_none()
    if not rfp:
        return []

    docs_result = await session.execute(
        select(KnowledgeBaseDocument).where(
            KnowledgeBaseDocument.user_id == user_id,
            KnowledgeBaseDocument.document_type == DocumentType.PAST_PERFORMANCE,
        )
    )
    docs = docs_result.scalars().all()

    matches = []
    for doc in docs:
        score = 0.0
        criteria: list[str] = []

        # NAICS match
        if doc.naics_code and rfp.naics_code and doc.naics_code == rfp.naics_code:
            score += 30.0
            criteria.append(f"NAICS code match: {doc.naics_code}")

        # Agency match
        if doc.performing_agency and rfp.agency:
            if (
                doc.performing_agency.lower() in rfp.agency.lower()
                or rfp.agency.lower() in doc.performing_agency.lower()
            ):
                score += 25.0
                criteria.append(f"Agency match: {doc.performing_agency}")

        # Contract value proximity (within 2x range)
        if doc.contract_value and rfp.estimated_value:
            ratio = doc.contract_value / rfp.estimated_value if rfp.estimated_value > 0 else 0
            if 0.5 <= ratio <= 2.0:
                score += 20.0
                criteria.append(f"Similar contract value: ${doc.contract_value:,.0f}")

        # Relevance tags overlap with RFP title/description keywords
        if doc.relevance_tags:
            rfp_text = f"{rfp.title} {rfp.description or ''}".lower()
            tag_matches = [tag for tag in doc.relevance_tags if tag.lower() in rfp_text]
            if tag_matches:
                score += min(25.0, len(tag_matches) * 5.0)
                criteria.append(f"Tag matches: {', '.join(tag_matches[:5])}")

        # Recency bonus
        if doc.period_of_performance_end:
            years_ago = (datetime.utcnow() - doc.period_of_performance_end).days / 365.25
            if years_ago <= 3:
                score += 10.0
                criteria.append("Recent performance (within 3 years)")
            elif years_ago <= 5:
                score += 5.0
                criteria.append("Relevant performance (within 5 years)")

        if score > 0:
            matches.append(
                PastPerformanceMatch(
                    document_id=doc.id,
                    title=doc.title,
                    score=min(score, 100.0),
                    matching_criteria=criteria,
                )
            )

    matches.sort(key=lambda m: m.score, reverse=True)
    return matches


async def generate_narrative(
    session: AsyncSession,
    doc_id: int,
    rfp_id: int,
    user_id: int,
) -> str | None:
    """Generate a tailored past performance narrative."""
    doc_result = await session.execute(
        select(KnowledgeBaseDocument).where(
            KnowledgeBaseDocument.id == doc_id,
            KnowledgeBaseDocument.user_id == user_id,
        )
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        return None

    rfp_result = await session.execute(select(RFP).where(RFP.id == rfp_id, RFP.user_id == user_id))
    rfp = rfp_result.scalar_one_or_none()
    if not rfp:
        return None

    parts = [f"# Past Performance: {doc.title}\n"]

    if doc.contract_number:
        parts.append(f"**Contract Number:** {doc.contract_number}")
    if doc.performing_agency:
        parts.append(f"**Agency:** {doc.performing_agency}")
    if doc.contract_value:
        parts.append(f"**Contract Value:** ${doc.contract_value:,.2f}")
    if doc.period_of_performance_start and doc.period_of_performance_end:
        parts.append(
            f"**Period of Performance:** {doc.period_of_performance_start.strftime('%m/%Y')} - "
            f"{doc.period_of_performance_end.strftime('%m/%Y')}"
        )
    if doc.naics_code:
        parts.append(f"**NAICS Code:** {doc.naics_code}")

    parts.append(f"\n**Relevance to {rfp.title}:**")
    parts.append(
        f"This past performance demonstrates our capability to deliver similar work "
        f"for {doc.performing_agency or 'the government'}."
    )

    if doc.full_text:
        summary = doc.full_text[:500].strip()
        if len(doc.full_text) > 500:
            summary += "..."
        parts.append(f"\n**Summary:**\n{summary}")

    return "\n".join(parts)
