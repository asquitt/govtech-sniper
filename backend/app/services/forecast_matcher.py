"""
Forecast matching service — matches procurement forecasts to existing RFPs.
"""

from typing import List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.rfp import RFP
from app.models.forecast import ProcurementForecast, ForecastAlert


async def run_forecast_matching(
    session: AsyncSession, user_id: int
) -> List[ForecastAlert]:
    """
    Match user's forecasts to their RFPs based on:
    - Agency (exact match, 30 points)
    - NAICS code (prefix match, 25 points)
    - Title keyword overlap (20 points)
    - Value range within ±50% (25 points)
    """
    forecasts_result = await session.execute(
        select(ProcurementForecast).where(
            ProcurementForecast.user_id == user_id,
            ProcurementForecast.linked_rfp_id.is_(None),  # type: ignore[union-attr]
        )
    )
    forecasts = forecasts_result.scalars().all()

    rfps_result = await session.execute(
        select(RFP).where(RFP.user_id == user_id)
    )
    rfps = rfps_result.scalars().all()

    new_alerts: List[ForecastAlert] = []

    for forecast in forecasts:
        for rfp in rfps:
            score, reasons = _compute_match(forecast, rfp)
            if score < 30:
                continue

            # Check if alert already exists
            existing = await session.execute(
                select(ForecastAlert).where(
                    ForecastAlert.forecast_id == forecast.id,
                    ForecastAlert.rfp_id == rfp.id,
                )
            )
            if existing.scalar_one_or_none():
                continue

            alert = ForecastAlert(
                user_id=user_id,
                forecast_id=forecast.id,
                rfp_id=rfp.id,
                match_score=score,
                match_reason="; ".join(reasons),
            )
            session.add(alert)
            new_alerts.append(alert)

    if new_alerts:
        await session.flush()

    return new_alerts


def _compute_match(
    forecast: ProcurementForecast, rfp: RFP
) -> Tuple[float, List[str]]:
    """Compute match score between a forecast and an RFP."""
    score = 0.0
    reasons: List[str] = []

    # Agency match (30 points)
    if forecast.agency and rfp.agency:
        if forecast.agency.lower() == rfp.agency.lower():
            score += 30
            reasons.append("Agency match")

    # NAICS prefix match (25 points)
    if forecast.naics_code and rfp.naics_code:
        f_naics = forecast.naics_code.strip()
        r_naics = rfp.naics_code.strip()
        if f_naics == r_naics:
            score += 25
            reasons.append("NAICS exact match")
        elif r_naics.startswith(f_naics[:4]) or f_naics.startswith(r_naics[:4]):
            score += 15
            reasons.append("NAICS prefix match")

    # Title keyword overlap (20 points)
    if forecast.title and rfp.title:
        f_words = set(forecast.title.lower().split())
        r_words = set(rfp.title.lower().split())
        # Remove common words
        stopwords = {"the", "a", "an", "and", "or", "for", "of", "to", "in", "services"}
        f_words -= stopwords
        r_words -= stopwords
        if f_words and r_words:
            overlap = len(f_words & r_words) / max(len(f_words), len(r_words))
            if overlap > 0.3:
                score += 20 * overlap
                reasons.append(f"Title overlap ({overlap:.0%})")

    # Value range match ±50% (25 points)
    if forecast.estimated_value and rfp.estimated_value:
        ratio = forecast.estimated_value / rfp.estimated_value
        if 0.5 <= ratio <= 2.0:
            proximity = 1.0 - abs(1.0 - ratio)
            score += 25 * max(proximity, 0)
            reasons.append("Value range match")

    return score, reasons
