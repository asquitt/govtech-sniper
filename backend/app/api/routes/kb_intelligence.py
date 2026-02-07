"""
RFP Sniper - Knowledge Base Intelligence Routes
================================================
Content freshness, auto-tagging, gap analysis, and duplicate detection.
"""

from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import UserAuth, get_current_user, resolve_user_id
from app.database import get_session
from app.models.knowledge_base import DocumentType, KnowledgeBaseDocument, ProcessingStatus

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/kb-intelligence", tags=["Knowledge Base Intelligence"])

# Freshness thresholds (days)
FRESHNESS_THRESHOLDS = {
    "fresh": 365,  # Updated within 1 year
    "aging": 730,  # 1-2 years old
    "stale": 1095,  # 2-3 years old
    "outdated": 99999,  # 3+ years old
}


@router.get("/freshness")
async def get_content_freshness(
    user_id: int | None = Query(default=None),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Content freshness analysis - flag outdated documents by type.
    Uses period_of_performance_end for past performance, updated_at for others.
    """
    uid = resolve_user_id(user_id, current_user)
    now = datetime.utcnow()

    docs = (
        await session.exec(
            select(KnowledgeBaseDocument).where(
                KnowledgeBaseDocument.user_id == uid,
                KnowledgeBaseDocument.processing_status == ProcessingStatus.READY,
            )
        )
    ).all()

    freshness_report: list[dict] = []
    summary = {"fresh": 0, "aging": 0, "stale": 0, "outdated": 0}

    for doc in docs:
        # Use performance end date for PP, otherwise updated_at
        if doc.document_type == DocumentType.PAST_PERFORMANCE and doc.period_of_performance_end:
            age_date = doc.period_of_performance_end
        else:
            age_date = doc.updated_at

        age_days = (now - age_date).days
        status = "outdated"
        for label, threshold in FRESHNESS_THRESHOLDS.items():
            if age_days <= threshold:
                status = label
                break

        summary[status] += 1
        freshness_report.append(
            {
                "id": doc.id,
                "title": doc.title,
                "document_type": doc.document_type.value,
                "age_days": age_days,
                "freshness": status,
                "last_updated": age_date.isoformat(),
                "times_cited": doc.times_cited,
                "last_cited_at": doc.last_cited_at.isoformat() if doc.last_cited_at else None,
            }
        )

    # Sort by staleness (most outdated first)
    freshness_report.sort(key=lambda x: x["age_days"], reverse=True)

    return {
        "summary": summary,
        "total_documents": len(docs),
        "documents": freshness_report,
    }


@router.get("/gap-analysis")
async def get_gap_analysis(
    user_id: int | None = Query(default=None),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Content gap analysis - identify what's missing from the knowledge base.
    Checks coverage across document types, NAICS codes, and agencies.
    """
    uid = resolve_user_id(user_id, current_user)

    docs = (
        await session.exec(
            select(KnowledgeBaseDocument).where(
                KnowledgeBaseDocument.user_id == uid,
                KnowledgeBaseDocument.processing_status == ProcessingStatus.READY,
            )
        )
    ).all()

    # Document type coverage
    type_counts: dict[str, int] = {}
    for dt in DocumentType:
        type_counts[dt.value] = 0
    for doc in docs:
        type_counts[doc.document_type.value] = type_counts.get(doc.document_type.value, 0) + 1

    # Required types with 0 docs = gaps
    critical_types = [
        DocumentType.PAST_PERFORMANCE,
        DocumentType.RESUME,
        DocumentType.CAPABILITY_STATEMENT,
    ]
    type_gaps = [
        {
            "type": dt.value,
            "label": dt.value.replace("_", " ").title(),
            "count": type_counts.get(dt.value, 0),
        }
        for dt in critical_types
        if type_counts.get(dt.value, 0) == 0
    ]

    # NAICS coverage from past performance docs
    naics_codes = set()
    agencies = set()
    for doc in docs:
        if doc.naics_code:
            naics_codes.add(doc.naics_code)
        if doc.performing_agency:
            agencies.add(doc.performing_agency)

    # Uncited docs (uploaded but never used in proposals)
    uncited = [
        {"id": doc.id, "title": doc.title, "type": doc.document_type.value}
        for doc in docs
        if doc.times_cited == 0
    ]

    # Stale past performance (>3 years)
    now = datetime.utcnow()
    stale_pp = [
        {
            "id": doc.id,
            "title": doc.title,
            "age_years": round((now - doc.period_of_performance_end).days / 365, 1),
        }
        for doc in docs
        if doc.document_type == DocumentType.PAST_PERFORMANCE
        and doc.period_of_performance_end
        and (now - doc.period_of_performance_end).days > 1095
    ]

    # Build recommendations
    recommendations: list[dict] = []
    if type_gaps:
        for gap in type_gaps:
            recommendations.append(
                {
                    "type": "gap",
                    "message": f"Missing {gap['label']} documents. Upload at least one for stronger proposals.",
                }
            )
    if len(naics_codes) < 3:
        recommendations.append(
            {
                "type": "coverage",
                "message": f"Only {len(naics_codes)} NAICS codes covered. Broader coverage improves AI matching.",
            }
        )
    if stale_pp:
        recommendations.append(
            {
                "type": "freshness",
                "message": f"{len(stale_pp)} past performance records are over 3 years old. Consider updating or replacing.",
            }
        )
    if len(uncited) > 5:
        recommendations.append(
            {
                "type": "utilization",
                "message": f"{len(uncited)} documents have never been cited. Review for relevance.",
            }
        )

    return {
        "type_coverage": type_counts,
        "type_gaps": type_gaps,
        "naics_codes_covered": len(naics_codes),
        "agencies_covered": len(agencies),
        "uncited_documents": uncited[:20],
        "stale_past_performance": stale_pp,
        "recommendations": recommendations,
    }


@router.post("/{document_id}/auto-tag")
async def auto_tag_document(
    document_id: int,
    user_id: int | None = Query(default=None),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Auto-tag a document based on its content and metadata.
    Extracts topic, agency, contract type tags from title and extracted text.
    """
    uid = resolve_user_id(user_id, current_user)

    doc = (
        await session.exec(
            select(KnowledgeBaseDocument).where(
                KnowledgeBaseDocument.id == document_id,
                KnowledgeBaseDocument.user_id == uid,
            )
        )
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Rule-based auto-tagging from title + metadata
    tags = set(doc.tags or [])
    text = (doc.title + " " + (doc.description or "")).lower()

    # Agency tags
    agency_keywords = {
        "dod": ["dod", "department of defense", "army", "navy", "air force", "marine"],
        "hhs": ["hhs", "health and human services", "cdc", "nih", "fda"],
        "dhs": ["dhs", "homeland security", "fema", "cbp", "tsa", "ice"],
        "nasa": ["nasa", "space", "aerospace"],
        "va": ["va", "veterans affairs", "veteran"],
        "gsa": ["gsa", "general services"],
        "doe": ["doe", "energy"],
        "usda": ["usda", "agriculture"],
    }
    for tag, keywords in agency_keywords.items():
        if any(kw in text for kw in keywords):
            tags.add(f"agency:{tag}")

    # Domain tags
    domain_keywords = {
        "cybersecurity": ["cyber", "security", "infosec", "soc ", "siem", "zero trust"],
        "cloud": ["cloud", "aws", "azure", "gcp", "saas", "iaas"],
        "data-analytics": ["data", "analytics", "bi ", "business intelligence", "dashboard"],
        "software-dev": ["software", "development", "agile", "devops", "ci/cd"],
        "it-infrastructure": ["infrastructure", "network", "server", "storage", "data center"],
        "healthcare-it": ["health it", "ehr", "emr", "hipaa", "medical"],
        "ai-ml": ["artificial intelligence", "machine learning", "nlp", "deep learning", "ai "],
    }
    for tag, keywords in domain_keywords.items():
        if any(kw in text for kw in keywords):
            tags.add(f"domain:{tag}")

    # Contract type tags
    contract_keywords = {
        "idiq": ["idiq", "indefinite delivery"],
        "t&m": ["t&m", "time and material"],
        "ffp": ["ffp", "firm fixed"],
        "cpff": ["cpff", "cost plus"],
        "bpa": ["bpa", "blanket purchase"],
    }
    for tag, keywords in contract_keywords.items():
        if any(kw in text for kw in keywords):
            tags.add(f"contract:{tag}")

    # Document type tag
    tags.add(f"type:{doc.document_type.value}")

    # NAICS tag
    if doc.naics_code:
        tags.add(f"naics:{doc.naics_code}")

    # Agency tag from performing_agency
    if doc.performing_agency:
        tags.add(f"agency-name:{doc.performing_agency.lower().replace(' ', '-')[:30]}")

    doc.tags = sorted(tags)
    doc.updated_at = datetime.utcnow()
    session.add(doc)
    await session.commit()

    return {"document_id": doc.id, "tags": doc.tags, "tags_added": len(tags) - len(doc.tags or [])}


@router.get("/duplicates")
async def detect_duplicates(
    user_id: int | None = Query(default=None),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Detect potential duplicate documents based on title similarity and metadata.
    """
    uid = resolve_user_id(user_id, current_user)

    docs = (
        await session.exec(
            select(KnowledgeBaseDocument)
            .where(
                KnowledgeBaseDocument.user_id == uid,
                KnowledgeBaseDocument.processing_status == ProcessingStatus.READY,
            )
            .order_by(KnowledgeBaseDocument.title)
        )
    ).all()

    duplicates: list[dict] = []
    seen: dict[str, list[dict]] = {}

    for doc in docs:
        # Normalize title for comparison
        normalized = doc.title.lower().strip()
        # Remove common suffixes like (1), _v2, -copy
        for suffix in ["(1)", "(2)", "(3)", "_v2", "_v3", "-copy", " copy", "_final", "_draft"]:
            normalized = normalized.replace(suffix, "")
        normalized = normalized.strip()

        key = normalized
        entry = {
            "id": doc.id,
            "title": doc.title,
            "type": doc.document_type.value,
            "size": doc.file_size_bytes,
        }

        if key in seen:
            seen[key].append(entry)
        else:
            seen[key] = [entry]

    # Also check contract_number duplicates
    contract_groups: dict[str, list[dict]] = {}
    for doc in docs:
        if doc.contract_number:
            cn = doc.contract_number.strip().upper()
            entry = {"id": doc.id, "title": doc.title, "contract_number": doc.contract_number}
            if cn in contract_groups:
                contract_groups[cn].append(entry)
            else:
                contract_groups[cn] = [entry]

    # Collect groups with >1 doc
    for key, group in seen.items():
        if len(group) > 1:
            duplicates.append({"match_type": "title", "key": key, "documents": group})

    for cn, group in contract_groups.items():
        if len(group) > 1:
            duplicates.append({"match_type": "contract_number", "key": cn, "documents": group})

    return {
        "duplicate_groups": duplicates,
        "total_potential_duplicates": sum(len(g["documents"]) for g in duplicates),
    }
