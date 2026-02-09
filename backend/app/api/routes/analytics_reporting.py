"""
RFP Sniper - Analytics Reporting Routes
========================================
Win rates, pipeline, conversion, turnaround, NAICS performance, and export.
"""

import csv
import io
from datetime import datetime, timedelta

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import case, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import UserAuth, get_current_user
from app.database import get_session
from app.models.capture import CapturePlan, CaptureStage
from app.models.proposal import Proposal, ProposalStatus
from app.models.rfp import RFP
from app.schemas.analytics import ExportRequest

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics Reporting"])


# =============================================================================
# SQL Dialect Helpers
# =============================================================================


def _is_sqlite(session: AsyncSession) -> bool:
    bind = session.get_bind()
    return bool(bind and bind.dialect.name == "sqlite")


def _month_expr(session: AsyncSession, value):
    if _is_sqlite(session):
        return func.strftime("%Y-%m", value)
    return func.to_char(value, "YYYY-MM")


def _days_between_expr(session: AsyncSession, end_value, start_value):
    if _is_sqlite(session):
        return func.julianday(end_value) - func.julianday(start_value)
    return func.extract("epoch", end_value - start_value) / 86400


# =============================================================================
# Win Rate
# =============================================================================


@router.get("/win-rate")
async def get_win_rate(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Win/loss rate from CapturePlan stages with monthly trend."""
    user_id = current_user.id

    stage_counts = await session.execute(
        select(
            CapturePlan.stage,
            func.count(CapturePlan.id).label("count"),
        )
        .where(
            CapturePlan.owner_id == user_id,
            CapturePlan.stage.in_([CaptureStage.WON, CaptureStage.LOST]),
        )
        .group_by(CapturePlan.stage)
    )
    counts_map = {row.stage: row.count for row in stage_counts.all()}
    total_won = counts_map.get(CaptureStage.WON, 0)
    total_lost = counts_map.get(CaptureStage.LOST, 0)
    denom = total_won + total_lost
    win_rate = round((total_won / denom * 100) if denom > 0 else 0.0, 1)

    # Monthly trend (last 12 months)
    twelve_months_ago = datetime.utcnow() - timedelta(days=365)
    month_expr = _month_expr(session, CapturePlan.updated_at)
    trend_rows = await session.execute(
        select(
            month_expr.label("month"),
            CapturePlan.stage,
            func.count(CapturePlan.id).label("count"),
        )
        .where(
            CapturePlan.owner_id == user_id,
            CapturePlan.stage.in_([CaptureStage.WON, CaptureStage.LOST]),
            CapturePlan.updated_at >= twelve_months_ago,
        )
        .group_by(
            month_expr,
            CapturePlan.stage,
        )
        .order_by(month_expr)
    )
    monthly: dict[str, dict[str, int]] = {}
    for row in trend_rows.all():
        monthly.setdefault(row.month, {"won": 0, "lost": 0})
        if row.stage == CaptureStage.WON:
            monthly[row.month]["won"] = row.count
        else:
            monthly[row.month]["lost"] = row.count

    trend = []
    for month, data in sorted(monthly.items()):
        w, l = data["won"], data["lost"]
        rate = round((w / (w + l) * 100) if (w + l) > 0 else 0.0, 1)
        trend.append({"month": month, "won": w, "lost": l, "rate": rate})

    return {
        "win_rate": win_rate,
        "total_won": total_won,
        "total_lost": total_lost,
        "trend": trend,
    }


# =============================================================================
# Pipeline by Stage
# =============================================================================


@router.get("/pipeline-by-stage")
async def get_pipeline_by_stage(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Aggregate RFP estimated_value and count per CapturePlan stage."""
    user_id = current_user.id

    results = await session.execute(
        select(
            CapturePlan.stage,
            func.count(CapturePlan.id).label("count"),
            func.coalesce(func.sum(RFP.estimated_value), 0).label("total_value"),
        )
        .join(RFP, RFP.id == CapturePlan.rfp_id)
        .where(CapturePlan.owner_id == user_id)
        .group_by(CapturePlan.stage)
    )

    stages = []
    total_pipeline = 0.0
    for row in results.all():
        val = float(row.total_value)
        stages.append(
            {
                "stage": row.stage.value,
                "count": row.count,
                "total_value": val,
            }
        )
        total_pipeline += val

    return {"stages": stages, "total_pipeline_value": total_pipeline}


# =============================================================================
# Conversion Rates
# =============================================================================


@router.get("/conversion-rates")
async def get_conversion_rates(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Stage-to-stage conversion rates through the capture funnel."""
    user_id = current_user.id

    ordered_stages = [
        CaptureStage.IDENTIFIED,
        CaptureStage.QUALIFIED,
        CaptureStage.PURSUIT,
        CaptureStage.PROPOSAL,
        CaptureStage.SUBMITTED,
        CaptureStage.WON,
    ]
    stage_index = {s: i for i, s in enumerate(ordered_stages)}

    stage_counts_result = await session.execute(
        select(
            CapturePlan.stage,
            func.count(CapturePlan.id).label("count"),
        )
        .where(CapturePlan.owner_id == user_id)
        .group_by(CapturePlan.stage)
    )
    raw_counts: dict[str, int] = {}
    for row in stage_counts_result.all():
        raw_counts[row.stage.value] = row.count

    # Build cumulative: items at stage N passed through 0..N-1
    cumulative: dict[str, int] = {}
    for stage in ordered_stages:
        idx = stage_index[stage]
        cumulative[stage.value] = sum(
            raw_counts.get(s.value, 0) for s in ordered_stages if stage_index[s] >= idx
        )
    # Lost items entered at identified
    cumulative[CaptureStage.IDENTIFIED.value] += raw_counts.get(CaptureStage.LOST.value, 0)

    conversions = []
    for i in range(len(ordered_stages) - 1):
        fs = ordered_stages[i]
        ts = ordered_stages[i + 1]
        cf = cumulative.get(fs.value, 0)
        ct = cumulative.get(ts.value, 0)
        rate = round((ct / cf * 100) if cf > 0 else 0.0, 1)
        conversions.append(
            {
                "from_stage": fs.value,
                "to_stage": ts.value,
                "count_from": cf,
                "count_to": ct,
                "rate": rate,
            }
        )

    total_id = cumulative.get(CaptureStage.IDENTIFIED.value, 0)
    total_won = cumulative.get(CaptureStage.WON.value, 0)
    overall = round((total_won / total_id * 100) if total_id > 0 else 0.0, 1)

    return {"conversions": conversions, "overall_rate": overall}


# =============================================================================
# Proposal Turnaround
# =============================================================================


@router.get("/proposal-turnaround")
async def get_proposal_turnaround(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Average days from RFP creation to Proposal creation (submitted+)."""
    user_id = current_user.id
    submitted_statuses = [ProposalStatus.SUBMITTED, ProposalStatus.FINAL]
    turnaround_days_expr = _days_between_expr(session, Proposal.created_at, RFP.created_at)

    overall_result = await session.execute(
        select(
            func.avg(turnaround_days_expr).label("avg_days"),
        )
        .join(RFP, RFP.id == Proposal.rfp_id)
        .where(
            Proposal.user_id == user_id,
            Proposal.status.in_(submitted_statuses),
        )
    )
    overall_avg = overall_result.scalar() or 0.0

    twelve_months_ago = datetime.utcnow() - timedelta(days=365)
    month_expr = _month_expr(session, Proposal.created_at)
    monthly_result = await session.execute(
        select(
            month_expr.label("month"),
            func.avg(turnaround_days_expr).label("avg_days"),
            func.count(Proposal.id).label("count"),
        )
        .join(RFP, RFP.id == Proposal.rfp_id)
        .where(
            Proposal.user_id == user_id,
            Proposal.status.in_(submitted_statuses),
            Proposal.created_at >= twelve_months_ago,
        )
        .group_by(month_expr)
        .order_by(month_expr)
    )

    trend = [
        {
            "month": row.month,
            "avg_days": round(float(row.avg_days), 1) if row.avg_days else 0.0,
            "count": row.count,
        }
        for row in monthly_result.all()
    ]

    return {"overall_avg_days": round(float(overall_avg), 1), "trend": trend}


# =============================================================================
# NAICS Performance
# =============================================================================


@router.get("/naics-performance")
async def get_naics_performance(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Win rates grouped by NAICS code (top 10 by volume)."""
    user_id = current_user.id

    results = await session.execute(
        select(
            RFP.naics_code,
            func.count(CapturePlan.id).label("total"),
            func.count(case((CapturePlan.stage == CaptureStage.WON, 1))).label("won"),
            func.count(case((CapturePlan.stage == CaptureStage.LOST, 1))).label("lost"),
        )
        .join(CapturePlan, CapturePlan.rfp_id == RFP.id)
        .where(
            CapturePlan.owner_id == user_id,
            RFP.naics_code.isnot(None),
            CapturePlan.stage.in_([CaptureStage.WON, CaptureStage.LOST]),
        )
        .group_by(RFP.naics_code)
        .order_by(func.count(CapturePlan.id).desc())
        .limit(10)
    )

    entries = []
    for row in results.all():
        denom = row.won + row.lost
        rate = round((row.won / denom * 100) if denom > 0 else 0.0, 1)
        entries.append(
            {
                "naics_code": row.naics_code,
                "total": row.total,
                "won": row.won,
                "lost": row.lost,
                "win_rate": rate,
            }
        )

    return {"entries": entries}


# =============================================================================
# Export
# =============================================================================


@router.post("/export")
async def export_analytics(
    body: ExportRequest,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """Export analytics data as CSV."""
    report_type = body.report_type

    if report_type == "win-rate":
        data = await get_win_rate(current_user=current_user, session=session)
        rows = data.get("trend", [])
        headers = ["month", "won", "lost", "rate"]
    elif report_type == "pipeline":
        data = await get_pipeline_by_stage(current_user=current_user, session=session)
        rows = data.get("stages", [])
        headers = ["stage", "count", "total_value"]
    elif report_type == "conversion":
        data = await get_conversion_rates(current_user=current_user, session=session)
        rows = data.get("conversions", [])
        headers = ["from_stage", "to_stage", "count_from", "count_to", "rate"]
    elif report_type == "turnaround":
        data = await get_proposal_turnaround(current_user=current_user, session=session)
        rows = data.get("trend", [])
        headers = ["month", "avg_days", "count"]
    elif report_type == "naics":
        data = await get_naics_performance(current_user=current_user, session=session)
        rows = data.get("entries", [])
        headers = ["naics_code", "total", "won", "lost", "win_rate"]
    else:
        raise HTTPException(status_code=400, detail=f"Unknown report_type: {report_type}")

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{report_type}_export.csv"'},
    )
