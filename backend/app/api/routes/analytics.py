"""
RFP Sniper - Analytics Routes
==============================
Dashboard metrics and reporting.
"""

from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, case
from sqlmodel import select
import structlog

from app.database import get_session
from app.models.rfp import RFP, RFPStatus, ComplianceMatrix
from app.models.proposal import Proposal, ProposalSection, SectionStatus, ProposalStatus
from app.models.knowledge_base import KnowledgeBaseDocument
from app.models.audit import AuditEvent
from app.models.integration import IntegrationConfig, IntegrationSyncRun, IntegrationSyncStatus, IntegrationWebhookEvent
from app.observability.metrics import get_metrics
from app.config import settings
from app.services.alert_service import get_alert_counts
from app.api.deps import get_current_user, UserAuth

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


# =============================================================================
# Dashboard Overview
# =============================================================================

@router.get("/dashboard")
async def get_dashboard_metrics(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Get dashboard overview metrics for the current user.
    """
    user_id = current_user.id

    # RFP counts by status
    rfp_counts = await session.execute(
        select(
            RFP.status,
            func.count(RFP.id).label("count"),
        ).where(RFP.user_id == user_id)
        .group_by(RFP.status)
    )
    rfp_by_status = {row.status.value: row.count for row in rfp_counts.all()}

    # Total RFPs
    total_rfps = sum(rfp_by_status.values())

    # Qualified RFPs
    qualified_result = await session.execute(
        select(func.count(RFP.id)).where(
            RFP.user_id == user_id,
            RFP.is_qualified == True,
        )
    )
    qualified_rfps = qualified_result.scalar() or 0

    # Proposals
    proposal_counts = await session.execute(
        select(
            Proposal.status,
            func.count(Proposal.id).label("count"),
        ).where(Proposal.user_id == user_id)
        .group_by(Proposal.status)
    )
    proposals_by_status = {row.status.value: row.count for row in proposal_counts.all()}
    total_proposals = sum(proposals_by_status.values())

    # Documents in knowledge base
    docs_result = await session.execute(
        select(func.count(KnowledgeBaseDocument.id)).where(
            KnowledgeBaseDocument.user_id == user_id
        )
    )
    total_documents = docs_result.scalar() or 0

    # Upcoming deadlines (next 7 days)
    upcoming_deadline = datetime.utcnow() + timedelta(days=7)
    deadlines_result = await session.execute(
        select(func.count(RFP.id)).where(
            RFP.user_id == user_id,
            RFP.response_deadline != None,
            RFP.response_deadline <= upcoming_deadline,
            RFP.response_deadline >= datetime.utcnow(),
            RFP.status.not_in([RFPStatus.SUBMITTED, RFPStatus.ARCHIVED]),
        )
    )
    upcoming_deadlines = deadlines_result.scalar() or 0

    return {
        "overview": {
            "total_rfps": total_rfps,
            "qualified_rfps": qualified_rfps,
            "total_proposals": total_proposals,
            "total_documents": total_documents,
            "upcoming_deadlines": upcoming_deadlines,
        },
        "rfps_by_status": rfp_by_status,
        "proposals_by_status": proposals_by_status,
    }


# =============================================================================
# RFP Analytics
# =============================================================================

@router.get("/rfps")
async def get_rfp_analytics(
    days: int = Query(30, ge=7, le=365),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Get RFP analytics for the specified time period.
    """
    user_id = current_user.id
    start_date = datetime.utcnow() - timedelta(days=days)

    # RFPs added over time
    rfps_over_time = await session.execute(
        select(
            func.date(RFP.created_at).label("date"),
            func.count(RFP.id).label("count"),
        ).where(
            RFP.user_id == user_id,
            RFP.created_at >= start_date,
        ).group_by(func.date(RFP.created_at))
        .order_by(func.date(RFP.created_at))
    )
    timeline = [{"date": str(row.date), "count": row.count} for row in rfps_over_time.all()]

    # By agency
    by_agency = await session.execute(
        select(
            RFP.agency,
            func.count(RFP.id).label("count"),
        ).where(
            RFP.user_id == user_id,
            RFP.created_at >= start_date,
        ).group_by(RFP.agency)
        .order_by(func.count(RFP.id).desc())
        .limit(10)
    )
    agencies = [{"agency": row.agency, "count": row.count} for row in by_agency.all()]

    # By NAICS code
    by_naics = await session.execute(
        select(
            RFP.naics_code,
            func.count(RFP.id).label("count"),
        ).where(
            RFP.user_id == user_id,
            RFP.naics_code != None,
            RFP.created_at >= start_date,
        ).group_by(RFP.naics_code)
        .order_by(func.count(RFP.id).desc())
        .limit(10)
    )
    naics = [{"naics_code": row.naics_code, "count": row.count} for row in by_naics.all()]

    # Qualification rate
    total_filtered = await session.execute(
        select(func.count(RFP.id)).where(
            RFP.user_id == user_id,
            RFP.is_qualified != None,
            RFP.created_at >= start_date,
        )
    )
    total = total_filtered.scalar() or 0

    qualified_filtered = await session.execute(
        select(func.count(RFP.id)).where(
            RFP.user_id == user_id,
            RFP.is_qualified == True,
            RFP.created_at >= start_date,
        )
    )
    qualified = qualified_filtered.scalar() or 0

    qualification_rate = (qualified / total * 100) if total > 0 else 0

    return {
        "period_days": days,
        "timeline": timeline,
        "top_agencies": agencies,
        "top_naics": naics,
        "qualification_rate": round(qualification_rate, 1),
        "total_analyzed": total,
        "total_qualified": qualified,
    }


# =============================================================================
# Proposal Analytics
# =============================================================================

@router.get("/proposals")
async def get_proposal_analytics(
    days: int = Query(30, ge=7, le=365),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Get proposal generation analytics.
    """
    user_id = current_user.id
    start_date = datetime.utcnow() - timedelta(days=days)

    # Total sections generated
    sections_result = await session.execute(
        select(
            func.count(ProposalSection.id).label("total"),
            func.count(case((ProposalSection.status == SectionStatus.GENERATED, 1))).label("generated"),
            func.count(case((ProposalSection.status == SectionStatus.APPROVED, 1))).label("approved"),
        ).join(Proposal, ProposalSection.proposal_id == Proposal.id)
        .where(
            Proposal.user_id == user_id,
            ProposalSection.created_at >= start_date,
        )
    )
    sections = sections_result.first()

    # Average completion rate
    proposals_result = await session.execute(
        select(
            func.avg(
                case(
                    (Proposal.total_sections > 0,
                     Proposal.completed_sections * 100.0 / Proposal.total_sections),
                    else_=0
                )
            ).label("avg_completion"),
        ).where(
            Proposal.user_id == user_id,
            Proposal.created_at >= start_date,
        )
    )
    avg_completion = proposals_result.scalar() or 0

    # Word count statistics
    word_stats = await session.execute(
        select(
            func.sum(ProposalSection.word_count).label("total_words"),
            func.avg(ProposalSection.word_count).label("avg_words"),
        ).join(Proposal, ProposalSection.proposal_id == Proposal.id)
        .where(
            Proposal.user_id == user_id,
            ProposalSection.word_count != None,
            ProposalSection.created_at >= start_date,
        )
    )
    words = word_stats.first()

    # Proposals over time
    proposals_over_time = await session.execute(
        select(
            func.date(Proposal.created_at).label("date"),
            func.count(Proposal.id).label("count"),
        ).where(
            Proposal.user_id == user_id,
            Proposal.created_at >= start_date,
        ).group_by(func.date(Proposal.created_at))
        .order_by(func.date(Proposal.created_at))
    )
    timeline = [{"date": str(row.date), "count": row.count} for row in proposals_over_time.all()]

    return {
        "period_days": days,
        "sections": {
            "total": sections.total if sections else 0,
            "generated": sections.generated if sections else 0,
            "approved": sections.approved if sections else 0,
        },
        "average_completion_rate": round(avg_completion, 1),
        "word_count": {
            "total": words.total_words if words and words.total_words else 0,
            "average_per_section": round(words.avg_words, 0) if words and words.avg_words else 0,
        },
        "timeline": timeline,
    }


# =============================================================================
# Document Analytics
# =============================================================================

@router.get("/documents")
async def get_document_analytics(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Get knowledge base document analytics.
    """
    user_id = current_user.id

    # Documents by type
    by_type = await session.execute(
        select(
            KnowledgeBaseDocument.document_type,
            func.count(KnowledgeBaseDocument.id).label("count"),
        ).where(KnowledgeBaseDocument.user_id == user_id)
        .group_by(KnowledgeBaseDocument.document_type)
    )
    doc_types = [{"type": row.document_type.value, "count": row.count} for row in by_type.all()]

    # Most cited documents
    most_cited = await session.execute(
        select(
            KnowledgeBaseDocument.original_filename,
            KnowledgeBaseDocument.times_cited,
            KnowledgeBaseDocument.document_type,
        ).where(
            KnowledgeBaseDocument.user_id == user_id,
            KnowledgeBaseDocument.times_cited > 0,
        ).order_by(KnowledgeBaseDocument.times_cited.desc())
        .limit(10)
    )
    cited = [
        {
            "filename": row.original_filename,
            "citations": row.times_cited,
            "type": row.document_type.value,
        }
        for row in most_cited.all()
    ]

    # Total storage
    storage = await session.execute(
        select(func.sum(KnowledgeBaseDocument.file_size_bytes)).where(
            KnowledgeBaseDocument.user_id == user_id
        )
    )
    total_bytes = storage.scalar() or 0

    # Total page count
    pages = await session.execute(
        select(func.sum(KnowledgeBaseDocument.page_count)).where(
            KnowledgeBaseDocument.user_id == user_id
        )
    )
    total_pages = pages.scalar() or 0

    return {
        "total_documents": sum(d["count"] for d in doc_types),
        "by_type": doc_types,
        "most_cited": cited,
        "storage_bytes": total_bytes,
        "storage_mb": round(total_bytes / (1024 * 1024), 2),
        "total_pages": total_pages,
    }


# =============================================================================
# AI Usage Analytics
# =============================================================================

@router.get("/ai-usage")
async def get_ai_usage(
    days: int = Query(30, ge=7, le=365),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Get AI usage and cost analytics.
    """
    user_id = current_user.id
    start_date = datetime.utcnow() - timedelta(days=days)

    # Estimate based on section generations (tokens used)
    # In production, track actual token usage
    sections_with_tokens = await session.execute(
        select(
            func.sum(
                func.cast(
                    func.coalesce(
                        ProposalSection.generated_content['tokens_used'].astext,
                        '0'
                    ),
                    type_=int
                )
            ).label("total_tokens"),
            func.count(ProposalSection.id).label("generations"),
        ).join(Proposal, ProposalSection.proposal_id == Proposal.id)
        .where(
            Proposal.user_id == user_id,
            ProposalSection.generated_content != None,
            ProposalSection.created_at >= start_date,
        )
    )
    usage = sections_with_tokens.first()

    total_tokens = usage.total_tokens if usage and usage.total_tokens else 0
    generations = usage.generations if usage else 0

    # Estimate costs (Gemini 1.5 Pro pricing as of 2024)
    # $0.00125 per 1K input tokens, $0.00375 per 1K output tokens
    # Rough estimate: 2:1 input:output ratio
    estimated_cost = (total_tokens * 0.00125 / 1000) + (total_tokens * 0.5 * 0.00375 / 1000)

    # Analysis operations
    matrices_result = await session.execute(
        select(func.count(ComplianceMatrix.id)).where(
            ComplianceMatrix.created_at >= start_date,
        ).join(RFP, ComplianceMatrix.rfp_id == RFP.id)
        .where(RFP.user_id == user_id)
    )
    analyses = matrices_result.scalar() or 0

    return {
        "period_days": days,
        "total_tokens": total_tokens,
        "total_generations": generations,
        "total_analyses": analyses,
        "estimated_cost_usd": round(estimated_cost, 2),
        "average_tokens_per_generation": round(total_tokens / generations, 0) if generations > 0 else 0,
    }
    }


# =============================================================================
# Observability & Ops Metrics
# =============================================================================

@router.get("/observability")
async def get_observability_metrics(
    days: int = Query(30, ge=1, le=365),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Operational metrics for integrations, audits, and webhook activity.
    """
    user_id = current_user.id
    start_date = datetime.utcnow() - timedelta(days=days)

    audit_result = await session.execute(
        select(func.count(AuditEvent.id)).where(
            AuditEvent.user_id == user_id,
            AuditEvent.created_at >= start_date,
        )
    )
    audit_total = audit_result.scalar() or 0

    sync_counts = await session.execute(
        select(
            IntegrationSyncRun.provider,
            IntegrationSyncRun.status,
            func.count(IntegrationSyncRun.id).label("count"),
        )
        .join(IntegrationConfig, IntegrationConfig.id == IntegrationSyncRun.integration_id)
        .where(
            IntegrationConfig.user_id == user_id,
            IntegrationSyncRun.started_at >= start_date,
        )
        .group_by(IntegrationSyncRun.provider, IntegrationSyncRun.status)
    )
    sync_by_provider: dict = {}
    sync_totals = {"total": 0, "success": 0, "failed": 0}
    for row in sync_counts.all():
        provider = row.provider.value
        sync_by_provider.setdefault(provider, {"total": 0, "success": 0, "failed": 0})
        sync_by_provider[provider]["total"] += row.count
        sync_totals["total"] += row.count
        if row.status == IntegrationSyncStatus.SUCCESS:
            sync_by_provider[provider]["success"] += row.count
            sync_totals["success"] += row.count
        elif row.status == IntegrationSyncStatus.FAILED:
            sync_by_provider[provider]["failed"] += row.count
            sync_totals["failed"] += row.count

    last_sync_result = await session.execute(
        select(func.max(IntegrationSyncRun.started_at))
        .join(IntegrationConfig, IntegrationConfig.id == IntegrationSyncRun.integration_id)
        .where(
            IntegrationConfig.user_id == user_id,
            IntegrationSyncRun.started_at >= start_date,
        )
    )
    last_sync_at = last_sync_result.scalar()

    webhook_counts = await session.execute(
        select(
            IntegrationWebhookEvent.provider,
            func.count(IntegrationWebhookEvent.id).label("count"),
        )
        .join(IntegrationConfig, IntegrationConfig.id == IntegrationWebhookEvent.integration_id)
        .where(
            IntegrationConfig.user_id == user_id,
            IntegrationWebhookEvent.received_at >= start_date,
        )
        .group_by(IntegrationWebhookEvent.provider)
    )
    webhook_by_provider = {
        row.provider.value: row.count for row in webhook_counts.all()
    }
    webhook_total = sum(webhook_by_provider.values())

    return {
        "period_days": days,
        "audit_events": {"total": audit_total},
        "integration_syncs": {
            "total": sync_totals["total"],
            "success": sync_totals["success"],
            "failed": sync_totals["failed"],
            "last_sync_at": last_sync_at,
            "by_provider": sync_by_provider,
        },
        "webhook_events": {
            "total": webhook_total,
            "by_provider": webhook_by_provider,
        },
    }


# =============================================================================
# SLO & Alerting
# =============================================================================

@router.get("/slo")
async def get_slo_metrics(
    days: int = Query(7, ge=1, le=90),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    _ = current_user
    metrics = get_metrics().get_all()
    counters = metrics.get("counters", {})
    histograms = metrics.get("histograms", {})

    request_total = sum(
        value for key, value in counters.items() if key.startswith("http.requests")
    )
    error_total = sum(
        value for key, value in counters.items() if key.startswith("http.5xx_errors")
    )
    error_rate = (error_total / request_total) if request_total else 0.0

    latency_p95_values = [
        histogram.get("p95", 0)
        for key, histogram in histograms.items()
        if key.startswith("http.request_duration_ms")
    ]
    latency_p95 = max(latency_p95_values) if latency_p95_values else 0

    start_date = datetime.utcnow() - timedelta(days=days)
    sync_counts = await session.execute(
        select(
            IntegrationSyncRun.status,
            func.count(IntegrationSyncRun.id).label("count"),
        )
        .join(IntegrationConfig, IntegrationConfig.id == IntegrationSyncRun.integration_id)
        .where(IntegrationSyncRun.started_at >= start_date)
        .group_by(IntegrationSyncRun.status)
    )
    sync_totals = {"total": 0, "failed": 0}
    for row in sync_counts.all():
        sync_totals["total"] += row.count
        if row.status == IntegrationSyncStatus.FAILED:
            sync_totals["failed"] += row.count

    sync_failure_rate = (
        sync_totals["failed"] / sync_totals["total"]
        if sync_totals["total"]
        else 0.0
    )

    return {
        "targets": {
            "latency_p95_ms": settings.slo_latency_p95_ms,
            "error_rate": settings.slo_error_rate,
        },
        "observed": {
            "request_total": request_total,
            "error_rate": round(error_rate, 4),
            "latency_p95_ms": round(latency_p95, 2),
            "sync_failure_rate": round(sync_failure_rate, 4),
        },
        "within_slo": {
            "latency_p95": latency_p95 <= settings.slo_latency_p95_ms,
            "error_rate": error_rate <= settings.slo_error_rate,
        },
    }


@router.get("/alerts")
async def get_operational_alerts(
    days: int = Query(7, ge=1, le=90),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    user_id = current_user.id
    counts = await get_alert_counts(session, user_id=user_id, days=days)
    sync_failed_count = counts["sync_failures"]
    webhook_failed_count = counts["webhook_failures"]
    auth_failed_count = counts["auth_failures"]

    alerts = [
        {
            "type": "integration_sync_failures",
            "count": sync_failed_count,
            "threshold": settings.alert_sync_failures_threshold,
            "status": "triggered" if sync_failed_count >= settings.alert_sync_failures_threshold else "ok",
        },
        {
            "type": "webhook_failures",
            "count": webhook_failed_count,
            "threshold": settings.alert_webhook_failures_threshold,
            "status": "triggered" if webhook_failed_count >= settings.alert_webhook_failures_threshold else "ok",
        },
        {
            "type": "auth_failures",
            "count": auth_failed_count,
            "threshold": settings.alert_auth_failures_threshold,
            "status": "triggered" if auth_failed_count >= settings.alert_auth_failures_threshold else "ok",
        },
    ]

    return {
        "period_days": days,
        "alerts": alerts,
    }
