"""
Revenue forecasting and pipeline analytics routes.
"""

from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.capture import CapturePlan
from app.models.contract import ContractAward, ContractStatus
from app.models.rfp import RFP
from app.schemas.revenue import (
    AgencyRevenueResponse,
    AgencyRevenueSummary,
    PipelineStageSummary,
    PipelineSummaryResponse,
    RevenueTimelinePoint,
    RevenueTimelineResponse,
)
from app.services.auth_service import UserAuth

router = APIRouter(prefix="/revenue", tags=["Revenue"])


@router.get("/pipeline-summary", response_model=PipelineSummaryResponse)
async def get_pipeline_summary(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PipelineSummaryResponse:
    """
    Aggregate pipeline value by capture stage, weighted by win probability.
    """
    result = await session.execute(
        select(
            CapturePlan.stage,
            func.count(CapturePlan.id).label("count"),
            func.coalesce(func.sum(RFP.estimated_value), 0).label("unweighted"),
            func.coalesce(
                func.sum(RFP.estimated_value * CapturePlan.win_probability / 100.0),
                0,
            ).label("weighted"),
        )
        .join(RFP, RFP.id == CapturePlan.rfp_id)
        .where(CapturePlan.owner_id == current_user.id)
        .where(RFP.estimated_value.isnot(None))  # type: ignore[union-attr]
        .where(CapturePlan.win_probability.isnot(None))  # type: ignore[union-attr]
        .group_by(CapturePlan.stage)
    )
    rows = result.all()

    stages = []
    total_opp = 0
    total_uw = 0.0
    total_w = 0.0
    for row in rows:
        stage_name = row.stage.value if hasattr(row.stage, "value") else str(row.stage)
        stages.append(
            PipelineStageSummary(
                stage=stage_name,
                count=row.count,
                unweighted_value=float(row.unweighted),
                weighted_value=float(row.weighted),
            )
        )
        total_opp += row.count
        total_uw += float(row.unweighted)
        total_w += float(row.weighted)

    # Won contracts value
    won_result = await session.execute(
        select(func.coalesce(func.sum(ContractAward.value), 0)).where(
            ContractAward.user_id == current_user.id,
            ContractAward.status == ContractStatus.ACTIVE,
        )
    )
    won_value = float(won_result.scalar_one())

    return PipelineSummaryResponse(
        total_opportunities=total_opp,
        total_unweighted=total_uw,
        total_weighted=total_w,
        won_value=won_value,
        stages=stages,
    )


@router.get("/timeline", response_model=RevenueTimelineResponse)
async def get_revenue_timeline(
    granularity: str = Query("monthly", pattern="^(monthly|quarterly)$"),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> RevenueTimelineResponse:
    """
    Time-bucketed revenue by response_deadline (weighted pipeline) and
    contract start_date (won revenue).
    """
    # Pipeline opportunities with deadlines
    pipeline_result = await session.execute(
        select(
            RFP.response_deadline,
            RFP.estimated_value,
            CapturePlan.win_probability,
        )
        .join(CapturePlan, CapturePlan.rfp_id == RFP.id)
        .where(CapturePlan.owner_id == current_user.id)
        .where(RFP.response_deadline.isnot(None))  # type: ignore[union-attr]
        .where(RFP.estimated_value.isnot(None))  # type: ignore[union-attr]
        .where(CapturePlan.win_probability.isnot(None))  # type: ignore[union-attr]
    )
    pipeline_rows = pipeline_result.all()

    # Won contracts
    won_result = await session.execute(
        select(ContractAward.start_date, ContractAward.value).where(
            ContractAward.user_id == current_user.id,
            ContractAward.start_date.isnot(None),  # type: ignore[union-attr]
            ContractAward.value.isnot(None),  # type: ignore[union-attr]
        )
    )
    won_rows = won_result.all()

    buckets: dict[str, dict[str, float]] = defaultdict(
        lambda: {"weighted": 0.0, "won": 0.0, "count": 0}
    )

    for row in pipeline_rows:
        key = _period_key(row.response_deadline, granularity)
        weighted = float(row.estimated_value) * float(row.win_probability) / 100.0
        buckets[key]["weighted"] += weighted
        buckets[key]["count"] += 1

    for row in won_rows:
        key = _period_key(row.start_date, granularity)
        buckets[key]["won"] += float(row.value)

    points = sorted(
        [
            RevenueTimelinePoint(
                period=k,
                weighted_value=v["weighted"],
                won_value=v["won"],
                opportunity_count=int(v["count"]),
            )
            for k, v in buckets.items()
        ],
        key=lambda p: p.period,
    )

    return RevenueTimelineResponse(granularity=granularity, points=points)


@router.get("/by-agency", response_model=AgencyRevenueResponse)
async def get_revenue_by_agency(
    limit: int = Query(15, ge=1, le=50),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AgencyRevenueResponse:
    """
    Agency breakdown of pipeline + won revenue.
    """
    # Pipeline by agency
    pipeline_result = await session.execute(
        select(
            RFP.agency,
            func.count(CapturePlan.id).label("count"),
            func.coalesce(func.sum(RFP.estimated_value), 0).label("unweighted"),
            func.coalesce(
                func.sum(RFP.estimated_value * CapturePlan.win_probability / 100.0),
                0,
            ).label("weighted"),
        )
        .join(CapturePlan, CapturePlan.rfp_id == RFP.id)
        .where(CapturePlan.owner_id == current_user.id)
        .where(RFP.agency.isnot(None))  # type: ignore[union-attr]
        .where(RFP.estimated_value.isnot(None))  # type: ignore[union-attr]
        .where(CapturePlan.win_probability.isnot(None))  # type: ignore[union-attr]
        .group_by(RFP.agency)
        .order_by(func.sum(RFP.estimated_value * CapturePlan.win_probability / 100.0).desc())
        .limit(limit)
    )
    pipeline_rows = pipeline_result.all()

    # Won by agency
    won_result = await session.execute(
        select(
            ContractAward.agency,
            func.coalesce(func.sum(ContractAward.value), 0).label("won"),
        )
        .where(
            ContractAward.user_id == current_user.id,
            ContractAward.agency.isnot(None),  # type: ignore[union-attr]
            ContractAward.value.isnot(None),  # type: ignore[union-attr]
        )
        .group_by(ContractAward.agency)
    )
    won_map: dict[str, float] = {}
    for row in won_result.all():
        won_map[row.agency] = float(row.won)

    agencies = []
    for row in pipeline_rows:
        agencies.append(
            AgencyRevenueSummary(
                agency=row.agency,
                opportunity_count=row.count,
                unweighted_value=float(row.unweighted),
                weighted_value=float(row.weighted),
                won_value=won_map.get(row.agency, 0.0),
            )
        )

    return AgencyRevenueResponse(
        agencies=agencies,
        total_agencies=len(agencies),
    )


def _period_key(dt: datetime, granularity: str) -> str:
    """Convert a datetime to a period string (YYYY-MM or YYYY-QN)."""
    if granularity == "quarterly":
        quarter = (dt.month - 1) // 3 + 1
        return f"{dt.year}-Q{quarter}"
    return f"{dt.year}-{dt.month:02d}"
