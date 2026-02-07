"""
Procurement forecast CRUD and matching routes.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.forecast import ForecastAlert, ProcurementForecast
from app.models.rfp import RFP
from app.schemas.forecast import (
    ForecastAlertRead,
    ForecastCreate,
    ForecastRead,
    ForecastUpdate,
)
from app.services.audit_service import log_audit_event
from app.services.auth_service import UserAuth
from app.services.forecast_matcher import run_forecast_matching

router = APIRouter(prefix="/forecasts", tags=["Forecasts"])


@router.get("", response_model=list[ForecastRead])
async def list_forecasts(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ForecastRead]:
    result = await session.execute(
        select(ProcurementForecast)
        .where(ProcurementForecast.user_id == current_user.id)
        .order_by(ProcurementForecast.expected_solicitation_date.asc().nullslast())
    )
    forecasts = result.scalars().all()
    return [ForecastRead.model_validate(f) for f in forecasts]


@router.post("", response_model=ForecastRead)
async def create_forecast(
    payload: ForecastCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ForecastRead:
    forecast = ProcurementForecast(
        user_id=current_user.id,
        title=payload.title,
        agency=payload.agency,
        naics_code=payload.naics_code,
        estimated_value=payload.estimated_value,
        expected_solicitation_date=payload.expected_solicitation_date,
        expected_award_date=payload.expected_award_date,
        fiscal_year=payload.fiscal_year,
        source=payload.source,
        source_url=payload.source_url,
        description=payload.description,
    )
    session.add(forecast)
    await session.flush()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="procurement_forecast",
        entity_id=forecast.id,
        action="forecast.created",
        metadata={"title": forecast.title},
    )
    await session.commit()
    await session.refresh(forecast)

    return ForecastRead.model_validate(forecast)


@router.patch("/{forecast_id}", response_model=ForecastRead)
async def update_forecast(
    forecast_id: int,
    payload: ForecastUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ForecastRead:
    result = await session.execute(
        select(ProcurementForecast).where(
            ProcurementForecast.id == forecast_id,
            ProcurementForecast.user_id == current_user.id,
        )
    )
    forecast = result.scalar_one_or_none()
    if not forecast:
        raise HTTPException(status_code=404, detail="Forecast not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(forecast, field, value)
    forecast.updated_at = datetime.utcnow()

    await session.commit()
    await session.refresh(forecast)

    return ForecastRead.model_validate(forecast)


@router.delete("/{forecast_id}")
async def delete_forecast(
    forecast_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(
        select(ProcurementForecast).where(
            ProcurementForecast.id == forecast_id,
            ProcurementForecast.user_id == current_user.id,
        )
    )
    forecast = result.scalar_one_or_none()
    if not forecast:
        raise HTTPException(status_code=404, detail="Forecast not found")

    await session.delete(forecast)
    await session.commit()

    return {"message": "Forecast deleted"}


@router.post("/{forecast_id}/link/{rfp_id}", response_model=ForecastRead)
async def link_forecast_to_rfp(
    forecast_id: int,
    rfp_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ForecastRead:
    result = await session.execute(
        select(ProcurementForecast).where(
            ProcurementForecast.id == forecast_id,
            ProcurementForecast.user_id == current_user.id,
        )
    )
    forecast = result.scalar_one_or_none()
    if not forecast:
        raise HTTPException(status_code=404, detail="Forecast not found")

    rfp_result = await session.execute(
        select(RFP).where(RFP.id == rfp_id, RFP.user_id == current_user.id)
    )
    if not rfp_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="RFP not found")

    forecast.linked_rfp_id = rfp_id
    forecast.updated_at = datetime.utcnow()

    await session.commit()
    await session.refresh(forecast)

    return ForecastRead.model_validate(forecast)


@router.post("/match")
async def trigger_matching(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    new_alerts = await run_forecast_matching(session, current_user.id)
    await session.commit()
    return {"new_alerts": len(new_alerts)}


@router.get("/alerts", response_model=list[ForecastAlertRead])
async def list_alerts(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ForecastAlertRead]:
    result = await session.execute(
        select(ForecastAlert, ProcurementForecast.title, RFP.title)
        .join(
            ProcurementForecast,
            ProcurementForecast.id == ForecastAlert.forecast_id,
        )
        .join(RFP, RFP.id == ForecastAlert.rfp_id)
        .where(
            ForecastAlert.user_id == current_user.id,
            ForecastAlert.is_dismissed == False,
        )
        .order_by(ForecastAlert.match_score.desc())
    )
    rows = result.all()

    return [
        ForecastAlertRead(
            id=alert.id,
            user_id=alert.user_id,
            forecast_id=alert.forecast_id,
            rfp_id=alert.rfp_id,
            match_score=alert.match_score,
            match_reason=alert.match_reason,
            is_dismissed=alert.is_dismissed,
            created_at=alert.created_at,
            forecast_title=forecast_title,
            rfp_title=rfp_title,
        )
        for alert, forecast_title, rfp_title in rows
    ]


@router.patch("/alerts/{alert_id}")
async def dismiss_alert(
    alert_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(
        select(ForecastAlert).where(
            ForecastAlert.id == alert_id,
            ForecastAlert.user_id == current_user.id,
        )
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.is_dismissed = True
    await session.commit()

    return {"message": "Alert dismissed"}
