"""
RFP Sniper - Intelligence & Analytics Routes
==============================================
Win/loss analysis, budget intelligence, pipeline forecasting, and KPIs.
"""

from collections import defaultdict
from datetime import datetime, timedelta

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import UserAuth, get_current_user
from app.database import get_session
from app.models.award import AwardRecord
from app.models.capture import (
    CapturePlan,
    CaptureStage,
    WinLossDebrief,
)
from app.models.contract import ContractAward, ContractStatus
from app.models.proposal import Proposal, ProposalStatus
from app.models.rfp import RFP

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/intelligence", tags=["Intelligence"])


# =============================================================================
# SQL Dialect Helpers
# =============================================================================


def _is_sqlite(session: AsyncSession) -> bool:
    bind = session.get_bind()
    return bool(bind and bind.dialect.name == "sqlite")


def _year_expr(session: AsyncSession, value):
    if _is_sqlite(session):
        return func.strftime("%Y", value)
    return func.to_char(value, "YYYY")


def _month_number_expr(session: AsyncSession, value):
    if _is_sqlite(session):
        return func.strftime("%m", value)
    return func.to_char(value, "MM")


def _days_between_expr(session: AsyncSession, end_value, start_value):
    if _is_sqlite(session):
        return func.julianday(end_value) - func.julianday(start_value)
    return func.extract("epoch", end_value - start_value) / 86400


# =============================================================================
# Win/Loss Analysis
# =============================================================================


@router.get("/win-loss")
async def get_win_loss_analysis(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Comprehensive win/loss analysis with debriefs, themes, and competitor intel."""
    user_id = current_user.id

    # Overall win/loss stats by agency
    agency_stats = await session.execute(
        select(
            RFP.agency,
            func.count(case((CapturePlan.stage == CaptureStage.WON, 1))).label("won"),
            func.count(case((CapturePlan.stage == CaptureStage.LOST, 1))).label("lost"),
            func.coalesce(
                func.avg(case((CapturePlan.stage == CaptureStage.WON, RFP.estimated_value))),
                0,
            ).label("avg_win_value"),
        )
        .join(CapturePlan, CapturePlan.rfp_id == RFP.id)
        .where(
            CapturePlan.owner_id == user_id,
            CapturePlan.stage.in_([CaptureStage.WON, CaptureStage.LOST]),
            RFP.agency.isnot(None),
        )
        .group_by(RFP.agency)
        .order_by(func.count(CapturePlan.id).desc())
        .limit(15)
    )
    by_agency = []
    for row in agency_stats.all():
        total = row.won + row.lost
        rate = round((row.won / total * 100) if total > 0 else 0.0, 1)
        by_agency.append(
            {
                "agency": row.agency,
                "won": row.won,
                "lost": row.lost,
                "win_rate": rate,
                "avg_win_value": float(row.avg_win_value),
            }
        )

    # Win/loss by contract size bucket
    size_buckets = await session.execute(
        select(
            case(
                (RFP.estimated_value < 100000, "Under $100K"),
                (RFP.estimated_value < 500000, "$100K-$500K"),
                (RFP.estimated_value < 1000000, "$500K-$1M"),
                (RFP.estimated_value < 5000000, "$1M-$5M"),
                else_="$5M+",
            ).label("size_bucket"),
            func.count(case((CapturePlan.stage == CaptureStage.WON, 1))).label("won"),
            func.count(case((CapturePlan.stage == CaptureStage.LOST, 1))).label("lost"),
        )
        .join(CapturePlan, CapturePlan.rfp_id == RFP.id)
        .where(
            CapturePlan.owner_id == user_id,
            CapturePlan.stage.in_([CaptureStage.WON, CaptureStage.LOST]),
            RFP.estimated_value.isnot(None),
        )
        .group_by("size_bucket")
    )
    by_size = []
    for row in size_buckets.all():
        total = row.won + row.lost
        rate = round((row.won / total * 100) if total > 0 else 0.0, 1)
        by_size.append(
            {
                "bucket": row.size_bucket,
                "won": row.won,
                "lost": row.lost,
                "win_rate": rate,
            }
        )

    # Recent debriefs
    debriefs_result = await session.execute(
        select(WinLossDebrief)
        .where(WinLossDebrief.user_id == user_id)
        .order_by(WinLossDebrief.created_at.desc())
        .limit(10)
    )
    debriefs = [
        {
            "id": d.id,
            "outcome": d.outcome.value,
            "source": d.source.value,
            "debrief_date": d.debrief_date.isoformat() if d.debrief_date else None,
            "win_themes": d.win_themes,
            "loss_factors": d.loss_factors,
            "winning_vendor": d.winning_vendor,
            "winning_price": d.winning_price,
            "our_price": d.our_price,
            "num_offerors": d.num_offerors,
            "technical_score": d.technical_score,
            "agency_feedback": d.agency_feedback[:200] if d.agency_feedback else None,
        }
        for d in debriefs_result.scalars().all()
    ]

    # Top win themes and loss factors from all debriefs
    all_debriefs = await session.execute(
        select(WinLossDebrief.win_themes, WinLossDebrief.loss_factors).where(
            WinLossDebrief.user_id == user_id
        )
    )
    theme_counts: dict[str, int] = defaultdict(int)
    factor_counts: dict[str, int] = defaultdict(int)
    for row in all_debriefs.all():
        for theme in row.win_themes or []:
            theme_counts[theme] += 1
        for factor in row.loss_factors or []:
            factor_counts[factor] += 1

    top_themes = sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    top_factors = sorted(factor_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    # Recommendations based on data
    recommendations = _generate_recommendations(by_agency, by_size, top_themes, top_factors)

    return {
        "by_agency": by_agency,
        "by_size": by_size,
        "debriefs": debriefs,
        "top_win_themes": [{"theme": t, "count": c} for t, c in top_themes],
        "top_loss_factors": [{"factor": f, "count": c} for f, c in top_factors],
        "recommendations": recommendations,
    }


@router.post("/debriefs")
async def create_debrief(
    capture_plan_id: int,
    outcome: str,
    source: str = "internal_review",
    agency_feedback: str | None = None,
    win_themes: list[str] | None = None,
    loss_factors: list[str] | None = None,
    winning_vendor: str | None = None,
    winning_price: int | None = None,
    our_price: int | None = None,
    num_offerors: int | None = None,
    technical_score: float | None = None,
    management_score: float | None = None,
    price_score: float | None = None,
    past_performance_score: float | None = None,
    lessons_learned: str | None = None,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Create a win/loss debrief for a capture plan."""
    from app.models.capture import DebriefSource

    debrief = WinLossDebrief(
        capture_plan_id=capture_plan_id,
        user_id=current_user.id,
        outcome=CaptureStage(outcome),
        source=DebriefSource(source),
        agency_feedback=agency_feedback,
        win_themes=win_themes or [],
        loss_factors=loss_factors or [],
        winning_vendor=winning_vendor,
        winning_price=winning_price,
        our_price=our_price,
        num_offerors=num_offerors,
        technical_score=technical_score,
        management_score=management_score,
        price_score=price_score,
        past_performance_score=past_performance_score,
        lessons_learned=lessons_learned,
    )
    session.add(debrief)
    await session.commit()
    await session.refresh(debrief)
    return {"id": debrief.id, "status": "created"}


# =============================================================================
# Budget Intelligence
# =============================================================================


@router.get("/budget")
async def get_budget_intelligence(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Agency budget intelligence from award data and RFP patterns."""
    user_id = current_user.id
    award_year_expr = _year_expr(session, AwardRecord.award_date)
    posted_month_expr = _month_number_expr(session, RFP.posted_date)

    # Agency spending from AwardRecords (market-wide intelligence)
    spending_result = await session.execute(
        select(
            AwardRecord.agency,
            award_year_expr.label("year"),
            func.count(AwardRecord.id).label("award_count"),
            func.coalesce(func.sum(AwardRecord.award_amount), 0).label("total_spend"),
            func.coalesce(func.avg(AwardRecord.award_amount), 0).label("avg_award"),
        )
        .where(
            AwardRecord.user_id == user_id,
            AwardRecord.award_date.isnot(None),
            AwardRecord.agency.isnot(None),
        )
        .group_by(AwardRecord.agency, award_year_expr)
        .order_by(award_year_expr.desc())
    )
    agency_spending: dict[str, list[dict]] = defaultdict(list)
    for row in spending_result.all():
        agency_spending[row.agency].append(
            {
                "year": row.year,
                "award_count": row.award_count,
                "total_spend": float(row.total_spend),
                "avg_award": float(row.avg_award),
            }
        )

    # Top agencies by total spend
    top_agencies = sorted(
        [
            {
                "agency": agency,
                "years": years,
                "total_spend": sum(y["total_spend"] for y in years),
            }
            for agency, years in agency_spending.items()
        ],
        key=lambda x: x["total_spend"],
        reverse=True,
    )[:15]

    # NAICS spending trends
    naics_result = await session.execute(
        select(
            AwardRecord.naics_code,
            award_year_expr.label("year"),
            func.count(AwardRecord.id).label("count"),
            func.coalesce(func.sum(AwardRecord.award_amount), 0).label("total"),
        )
        .where(
            AwardRecord.user_id == user_id,
            AwardRecord.naics_code.isnot(None),
            AwardRecord.award_date.isnot(None),
        )
        .group_by(AwardRecord.naics_code, award_year_expr)
        .order_by(func.sum(AwardRecord.award_amount).desc())
    )
    naics_spending: dict[str, list[dict]] = defaultdict(list)
    for row in naics_result.all():
        naics_spending[row.naics_code].append(
            {
                "year": row.year,
                "count": row.count,
                "total": float(row.total),
            }
        )

    top_naics = sorted(
        [
            {
                "naics_code": code,
                "years": years,
                "total_spend": sum(y["total"] for y in years),
            }
            for code, years in naics_spending.items()
        ],
        key=lambda x: x["total_spend"],
        reverse=True,
    )[:10]

    # Budget season detection: which months have the most RFPs posted?
    season_result = await session.execute(
        select(
            posted_month_expr.label("month"),
            func.count(RFP.id).label("count"),
        )
        .where(
            RFP.user_id == user_id,
            RFP.posted_date.isnot(None),
        )
        .group_by(posted_month_expr)
        .order_by(func.count(RFP.id).desc())
    )
    budget_season = [
        {"month": int(row.month), "rfp_count": row.count} for row in season_result.all()
    ]

    # Competitor award analysis: who's winning what
    competitor_result = await session.execute(
        select(
            AwardRecord.awardee_name,
            func.count(AwardRecord.id).label("wins"),
            func.coalesce(func.sum(AwardRecord.award_amount), 0).label("total_value"),
            func.coalesce(func.avg(AwardRecord.award_amount), 0).label("avg_value"),
        )
        .where(
            AwardRecord.user_id == user_id,
            AwardRecord.awardee_name.isnot(None),
        )
        .group_by(AwardRecord.awardee_name)
        .order_by(func.sum(AwardRecord.award_amount).desc())
        .limit(20)
    )
    top_competitors = [
        {
            "vendor": row.awardee_name,
            "wins": row.wins,
            "total_value": float(row.total_value),
            "avg_value": float(row.avg_value),
        }
        for row in competitor_result.all()
    ]

    return {
        "top_agencies": top_agencies,
        "top_naics": top_naics,
        "budget_season": budget_season,
        "top_competitors": top_competitors,
    }


# =============================================================================
# Pipeline Forecast & KPIs
# =============================================================================


@router.get("/pipeline-forecast")
async def get_pipeline_forecast(
    granularity: str = Query("quarterly", pattern="^(monthly|quarterly)$"),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Weighted pipeline forecast by period with confidence bands."""
    user_id = current_user.id

    # Active pipeline items with deadlines
    pipeline_result = await session.execute(
        select(
            RFP.response_deadline,
            RFP.estimated_value,
            CapturePlan.win_probability,
            CapturePlan.stage,
        )
        .join(CapturePlan, CapturePlan.rfp_id == RFP.id)
        .where(
            CapturePlan.owner_id == user_id,
            CapturePlan.stage.notin_([CaptureStage.WON, CaptureStage.LOST]),
            RFP.response_deadline.isnot(None),
            RFP.estimated_value.isnot(None),
            CapturePlan.win_probability.isnot(None),
        )
    )

    buckets: dict[str, dict] = defaultdict(
        lambda: {
            "weighted": 0.0,
            "optimistic": 0.0,
            "pessimistic": 0.0,
            "count": 0,
            "unweighted": 0.0,
        }
    )

    for row in pipeline_result.all():
        key = _period_key(row.response_deadline, granularity)
        value = float(row.estimated_value)
        prob = float(row.win_probability) / 100.0
        buckets[key]["weighted"] += value * prob
        buckets[key]["optimistic"] += value * min(prob * 1.3, 1.0)
        buckets[key]["pessimistic"] += value * prob * 0.7
        buckets[key]["count"] += 1
        buckets[key]["unweighted"] += value

    forecast = sorted(
        [
            {
                "period": k,
                "weighted_value": round(v["weighted"], 2),
                "optimistic_value": round(v["optimistic"], 2),
                "pessimistic_value": round(v["pessimistic"], 2),
                "opportunity_count": v["count"],
                "unweighted_value": round(v["unweighted"], 2),
            }
            for k, v in buckets.items()
        ],
        key=lambda p: p["period"],
    )

    total_weighted = sum(f["weighted_value"] for f in forecast)
    total_unweighted = sum(f["unweighted_value"] for f in forecast)

    return {
        "granularity": granularity,
        "forecast": forecast,
        "total_weighted": round(total_weighted, 2),
        "total_unweighted": round(total_unweighted, 2),
    }


@router.get("/kpis")
async def get_kpis(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Key performance indicators dashboard."""
    user_id = current_user.id

    # Win rate
    wl_result = await session.execute(
        select(
            func.count(case((CapturePlan.stage == CaptureStage.WON, 1))).label("won"),
            func.count(case((CapturePlan.stage == CaptureStage.LOST, 1))).label("lost"),
        ).where(
            CapturePlan.owner_id == user_id,
            CapturePlan.stage.in_([CaptureStage.WON, CaptureStage.LOST]),
        )
    )
    wl = wl_result.one()
    total_decided = wl.won + wl.lost
    win_rate = round((wl.won / total_decided * 100) if total_decided > 0 else 0.0, 1)

    # Active pipeline count & value
    pipeline_result = await session.execute(
        select(
            func.count(CapturePlan.id).label("count"),
            func.coalesce(func.sum(RFP.estimated_value), 0).label("value"),
            func.coalesce(
                func.sum(RFP.estimated_value * CapturePlan.win_probability / 100.0), 0
            ).label("weighted"),
        )
        .join(RFP, RFP.id == CapturePlan.rfp_id)
        .where(
            CapturePlan.owner_id == user_id,
            CapturePlan.stage.notin_([CaptureStage.WON, CaptureStage.LOST]),
        )
    )
    pipeline = pipeline_result.one()

    # Won revenue (active contracts)
    won_result = await session.execute(
        select(
            func.count(ContractAward.id).label("count"),
            func.coalesce(func.sum(ContractAward.value), 0).label("value"),
        ).where(
            ContractAward.user_id == user_id,
            ContractAward.status == ContractStatus.ACTIVE,
        )
    )
    won = won_result.one()

    # Proposals in progress
    proposals_result = await session.execute(
        select(func.count(Proposal.id)).where(
            Proposal.user_id == user_id,
            Proposal.status.in_([ProposalStatus.DRAFT, ProposalStatus.IN_PROGRESS]),
        )
    )
    active_proposals = proposals_result.scalar() or 0

    # Avg proposal turnaround (last 90 days)
    ninety_days_ago = datetime.utcnow() - timedelta(days=90)
    turnaround_days_expr = _days_between_expr(session, Proposal.created_at, RFP.created_at)
    turnaround_result = await session.execute(
        select(func.avg(turnaround_days_expr))
        .join(RFP, RFP.id == Proposal.rfp_id)
        .where(
            Proposal.user_id == user_id,
            Proposal.created_at >= ninety_days_ago,
            Proposal.status.in_([ProposalStatus.SUBMITTED, ProposalStatus.FINAL]),
        )
    )
    avg_turnaround = round(float(turnaround_result.scalar() or 0.0), 1)

    # Upcoming deadlines (next 30 days)
    thirty_days = datetime.utcnow() + timedelta(days=30)
    deadlines_result = await session.execute(
        select(func.count(RFP.id)).where(
            RFP.user_id == user_id,
            RFP.response_deadline.isnot(None),
            RFP.response_deadline <= thirty_days,
            RFP.response_deadline >= datetime.utcnow(),
        )
    )
    upcoming_deadlines = deadlines_result.scalar() or 0

    return {
        "win_rate": win_rate,
        "total_won": wl.won,
        "total_lost": wl.lost,
        "active_pipeline": {
            "count": pipeline.count,
            "unweighted_value": float(pipeline.value),
            "weighted_value": float(pipeline.weighted),
        },
        "won_revenue": {
            "count": won.count,
            "value": float(won.value),
        },
        "active_proposals": active_proposals,
        "avg_turnaround_days": avg_turnaround,
        "upcoming_deadlines": upcoming_deadlines,
    }


# =============================================================================
# Resource Allocation
# =============================================================================


@router.get("/resource-allocation")
async def get_resource_allocation(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Team workload: proposals per stage and section assignments."""
    user_id = current_user.id

    # Proposals by status
    proposals_by_status = await session.execute(
        select(
            Proposal.status,
            func.count(Proposal.id).label("count"),
        )
        .where(Proposal.user_id == user_id)
        .group_by(Proposal.status)
    )
    workload = [
        {"status": row.status.value, "count": row.count} for row in proposals_by_status.all()
    ]

    # Capture plans by stage (active workload)
    captures_by_stage = await session.execute(
        select(
            CapturePlan.stage,
            func.count(CapturePlan.id).label("count"),
        )
        .where(
            CapturePlan.owner_id == user_id,
            CapturePlan.stage.notin_([CaptureStage.WON, CaptureStage.LOST]),
        )
        .group_by(CapturePlan.stage)
    )
    capture_workload = [
        {"stage": row.stage.value, "count": row.count} for row in captures_by_stage.all()
    ]

    return {
        "proposal_workload": workload,
        "capture_workload": capture_workload,
    }


# =============================================================================
# Helpers
# =============================================================================


def _period_key(dt: datetime, granularity: str) -> str:
    """Convert datetime to period string."""
    if granularity == "quarterly":
        quarter = (dt.month - 1) // 3 + 1
        return f"{dt.year}-Q{quarter}"
    return f"{dt.year}-{dt.month:02d}"


def _generate_recommendations(
    by_agency: list[dict],
    by_size: list[dict],
    top_themes: list[tuple],
    top_factors: list[tuple],
) -> list[dict]:
    """Generate data-driven recommendations from win/loss patterns."""
    recs = []

    # Find strongest agencies
    strong_agencies = [a for a in by_agency if a["win_rate"] >= 50 and a["won"] >= 2]
    if strong_agencies:
        names = ", ".join(a["agency"] for a in strong_agencies[:3])
        recs.append(
            {
                "type": "strength",
                "title": "Strong agency relationships",
                "message": f"You win {strong_agencies[0]['win_rate']}%+ at {names}. "
                "Prioritize opportunities from these agencies.",
            }
        )

    # Find weak spots
    weak_agencies = [a for a in by_agency if a["win_rate"] < 30 and (a["won"] + a["lost"]) >= 3]
    if weak_agencies:
        names = ", ".join(a["agency"] for a in weak_agencies[:3])
        recs.append(
            {
                "type": "warning",
                "title": "Low win rate agencies",
                "message": f"Win rate below 30% at {names}. Review debriefs to identify patterns.",
            }
        )

    # Size bucket insights
    best_size = max(by_size, key=lambda x: x["win_rate"]) if by_size else None
    if best_size and best_size["win_rate"] > 0:
        recs.append(
            {
                "type": "insight",
                "title": f"Best performance in {best_size['bucket']} range",
                "message": f"Your win rate is {best_size['win_rate']}% for "
                f"{best_size['bucket']} contracts. Consider focusing here.",
            }
        )

    # Top themes
    if top_themes:
        theme_name = top_themes[0][0]
        recs.append(
            {
                "type": "strength",
                "title": f'Top win theme: "{theme_name}"',
                "message": f'"{theme_name}" appears in {top_themes[0][1]} wins. '
                "Emphasize this in future proposals.",
            }
        )

    # Top loss factors
    if top_factors:
        factor_name = top_factors[0][0]
        recs.append(
            {
                "type": "action",
                "title": f'Address top loss factor: "{factor_name}"',
                "message": f'"{factor_name}" appears in {top_factors[0][1]} losses. '
                "Develop a mitigation strategy.",
            }
        )

    return recs
