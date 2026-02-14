"""Industry events CRUD, ingestion, alerts, and calendar routes."""

from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.event import EventType, IndustryEvent
from app.models.market_signal import SignalSubscription
from app.models.rfp import RFP
from app.schemas.event import (
    EventAlertRead,
    EventAlertResponse,
    EventCreate,
    EventIngestResponse,
    EventRead,
    EventUpdate,
)
from app.services.auth_service import UserAuth

router = APIRouter(prefix="/events", tags=["Events"])

EVENT_KEYWORDS = (
    "industry day",
    "pre-proposal",
    "pre proposal",
    "pre-solicitation conference",
    "site visit",
    "bidder conference",
    "offeror conference",
    "webinar",
)


def _build_curated_candidates(now: datetime) -> list[dict]:
    """Curated baseline sources ensure deterministic ingestion without external dependencies."""
    current_month = now.strftime("%B %Y")
    return [
        {
            "title": f"DHS Small Business Industry Day ({current_month})",
            "agency": "Department of Homeland Security",
            "event_type": EventType.INDUSTRY_DAY,
            "date": now + timedelta(days=14),
            "location": "Washington, DC",
            "description": "Acquisition planning overview and Q&A for upcoming DHS IT procurements.",
            "registration_url": "https://www.dhs.gov/business-opportunities",
            "source": "curated:dhs-business-opportunities",
        },
        {
            "title": f"Air Force Pre-Solicitation Webinar ({current_month})",
            "agency": "Department of the Air Force",
            "event_type": EventType.PRE_SOLICITATION,
            "date": now + timedelta(days=21),
            "location": "Virtual",
            "description": "Program office webinar covering draft requirements and teaming guidance.",
            "registration_url": "https://sam.gov/",
            "source": "curated:sam-pre-solicitation",
        },
        {
            "title": f"VA Health IT Industry Briefing ({current_month})",
            "agency": "Department of Veterans Affairs",
            "event_type": EventType.CONFERENCE,
            "date": now + timedelta(days=30),
            "location": "Arlington, VA",
            "description": "Mission priorities, modernization roadmap, and vendor engagement guidance.",
            "registration_url": "https://www.va.gov/oal/business/",
            "source": "curated:va-business",
        },
    ]


def _classify_event_type(text: str) -> EventType:
    lowered = text.lower()
    if "pre-solicitation" in lowered or "pre solicitation" in lowered:
        return EventType.PRE_SOLICITATION
    if "webinar" in lowered:
        return EventType.WEBINAR
    if "industry day" in lowered:
        return EventType.INDUSTRY_DAY
    return EventType.CONFERENCE


def _infer_event_date(rfp: RFP, now: datetime) -> datetime:
    if rfp.posted_date and rfp.response_deadline and rfp.response_deadline > rfp.posted_date:
        midpoint = rfp.posted_date + (rfp.response_deadline - rfp.posted_date) / 2
        proposed = min(midpoint, rfp.response_deadline - timedelta(days=2))
    elif rfp.response_deadline:
        proposed = rfp.response_deadline - timedelta(days=7)
    elif rfp.posted_date:
        proposed = rfp.posted_date + timedelta(days=10)
    else:
        proposed = now + timedelta(days=10)
    if proposed < now:
        return now + timedelta(days=1)
    return proposed


def _event_key(title: str, agency: str | None, date_value: datetime) -> tuple[str, str, str]:
    return (
        title.strip().lower(),
        (agency or "").strip().lower(),
        date_value.date().isoformat(),
    )


def _score_event_alert(
    event: IndustryEvent,
    now: datetime,
    subscription: SignalSubscription | None,
) -> tuple[float, list[str], int]:
    score = 10.0
    reasons: list[str] = []
    haystack = f"{event.title} {event.description or ''}".lower()

    days_until = max(0, (event.date.date() - now.date()).days)
    if days_until <= 7:
        score += 20
        reasons.append("Happening within 7 days")
    elif days_until <= 21:
        score += 12
        reasons.append("Happening within 3 weeks")

    if event.event_type == EventType.INDUSTRY_DAY:
        score += 8
        reasons.append("Industry day format")

    if subscription:
        matched_agencies: list[str] = []
        for agency in subscription.agencies:
            agency_l = agency.lower().strip()
            if not agency_l:
                continue
            if (event.agency and agency_l in event.agency.lower()) or agency_l in haystack:
                matched_agencies.append(agency)
        if matched_agencies:
            score += 35
            reasons.append(f"Agency alignment ({matched_agencies[0]})")

        keyword_hits = [kw for kw in subscription.keywords if kw and kw.lower().strip() in haystack]
        if keyword_hits:
            keyword_bonus = min(25, len(keyword_hits) * 8)
            score += keyword_bonus
            reasons.append(f"Keyword matches ({', '.join(keyword_hits[:3])})")

        naics_hits = [
            code for code in subscription.naics_codes if code and code.lower().strip() in haystack
        ]
        if naics_hits:
            score += min(15, len(naics_hits) * 6)
            reasons.append(f"NAICS match ({', '.join(naics_hits[:2])})")

    return min(100.0, round(score, 1)), reasons, days_until


@router.get("", response_model=list[EventRead])
async def list_events(
    archived: bool = False,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[EventRead]:
    result = await session.execute(
        select(IndustryEvent)
        .where(
            IndustryEvent.user_id == current_user.id,
            IndustryEvent.is_archived == archived,
        )
        .order_by(IndustryEvent.date.asc())
    )
    events = result.scalars().all()
    return [EventRead.model_validate(e) for e in events]


@router.get("/upcoming", response_model=list[EventRead])
async def upcoming_events(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[EventRead]:
    now = datetime.utcnow()
    cutoff = now + timedelta(days=30)
    result = await session.execute(
        select(IndustryEvent)
        .where(
            IndustryEvent.user_id == current_user.id,
            IndustryEvent.is_archived == False,
            IndustryEvent.date >= now,
            IndustryEvent.date <= cutoff,
        )
        .order_by(IndustryEvent.date.asc())
    )
    events = result.scalars().all()
    return [EventRead.model_validate(e) for e in events]


@router.get("/calendar", response_model=list[EventRead])
async def calendar_events(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2020, le=2100),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[EventRead]:
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)

    result = await session.execute(
        select(IndustryEvent)
        .where(
            IndustryEvent.user_id == current_user.id,
            IndustryEvent.is_archived == False,
            IndustryEvent.date >= start,
            IndustryEvent.date < end,
        )
        .order_by(IndustryEvent.date.asc())
    )
    events = result.scalars().all()
    return [EventRead.model_validate(e) for e in events]


@router.post("/ingest", response_model=EventIngestResponse)
async def ingest_events(
    days_ahead: int = Query(default=90, ge=7, le=365),
    include_curated: bool = Query(default=True),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> EventIngestResponse:
    """Create events from curated government sources and event-like RFP language."""
    now = datetime.utcnow()
    horizon = now + timedelta(days=days_ahead)

    existing_result = await session.execute(
        select(IndustryEvent).where(IndustryEvent.user_id == current_user.id)
    )
    existing = existing_result.scalars().all()
    existing_keys = {_event_key(item.title, item.agency, item.date) for item in existing}

    candidates: list[dict] = []
    if include_curated:
        candidates.extend(_build_curated_candidates(now))

    rfp_result = await session.execute(
        select(RFP).where(
            RFP.user_id == current_user.id,
            or_(RFP.is_qualified.is_(None), RFP.is_qualified.is_(True)),
            RFP.response_deadline.isnot(None),
            RFP.response_deadline >= now,
            RFP.response_deadline <= horizon,
        )
    )
    for rfp in rfp_result.scalars().all():
        haystack = " ".join(
            [
                rfp.title or "",
                rfp.description or "",
                rfp.full_text or "",
            ]
        ).lower()
        if not any(keyword in haystack for keyword in EVENT_KEYWORDS):
            continue
        inferred_date = _infer_event_date(rfp, now)
        source_name = rfp.source_type or "sam.gov"
        candidates.append(
            {
                "title": f"{rfp.agency} Engagement Event: {rfp.title}"[:255],
                "agency": rfp.agency,
                "event_type": _classify_event_type(haystack),
                "date": inferred_date,
                "location": rfp.place_of_performance,
                "description": (
                    f"Derived from solicitation {rfp.solicitation_number}. "
                    "Detected event-related language in solicitation package."
                ),
                "registration_url": rfp.source_url or rfp.sam_gov_link,
                "source": f"rfp:{source_name}",
            }
        )

    created_ids: list[int] = []
    source_breakdown: defaultdict[str, int] = defaultdict(int)
    existing_count = 0
    for candidate in candidates:
        key = _event_key(
            str(candidate["title"]),
            candidate.get("agency"),
            candidate["date"],
        )
        if key in existing_keys:
            existing_count += 1
            continue
        event = IndustryEvent(
            user_id=current_user.id,
            title=str(candidate["title"]),
            agency=candidate.get("agency"),
            event_type=candidate["event_type"],
            date=candidate["date"],
            location=candidate.get("location"),
            registration_url=candidate.get("registration_url"),
            description=candidate.get("description"),
            source=candidate.get("source"),
        )
        session.add(event)
        await session.flush()
        created_ids.append(event.id)
        source_breakdown[str(candidate.get("source") or "unknown")] += 1
        existing_keys.add(key)

    await session.commit()
    return EventIngestResponse(
        created=len(created_ids),
        existing=existing_count,
        candidates=len(candidates),
        created_event_ids=created_ids,
        source_breakdown=dict(source_breakdown),
    )


@router.get("/alerts", response_model=EventAlertResponse)
async def event_alerts(
    days: int = Query(default=45, ge=1, le=180),
    min_score: float = Query(default=35, ge=0, le=100),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> EventAlertResponse:
    """Return upcoming events ranked by profile relevance and urgency."""
    now = datetime.utcnow()
    horizon = now + timedelta(days=days)
    events_result = await session.execute(
        select(IndustryEvent)
        .where(
            IndustryEvent.user_id == current_user.id,
            IndustryEvent.is_archived == False,
            IndustryEvent.date >= now,
            IndustryEvent.date <= horizon,
        )
        .order_by(IndustryEvent.date.asc())
    )
    events = events_result.scalars().all()

    sub_result = await session.execute(
        select(SignalSubscription).where(SignalSubscription.user_id == current_user.id)
    )
    subscription = sub_result.scalar_one_or_none()

    alerts: list[EventAlertRead] = []
    for event in events:
        score, reasons, days_until = _score_event_alert(event, now, subscription)
        if score < min_score:
            continue
        alerts.append(
            EventAlertRead(
                event=EventRead.model_validate(event),
                relevance_score=score,
                match_reasons=reasons,
                days_until_event=days_until,
            )
        )

    alerts.sort(
        key=lambda item: (
            -item.relevance_score,
            item.days_until_event,
            item.event.date,
        )
    )
    alerts = alerts[:limit]
    return EventAlertResponse(
        alerts=alerts,
        total=len(alerts),
        evaluated=len(events),
    )


@router.post("", response_model=EventRead)
async def create_event(
    payload: EventCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> EventRead:
    event = IndustryEvent(
        user_id=current_user.id,
        title=payload.title,
        agency=payload.agency,
        event_type=payload.event_type,
        date=payload.date,
        location=payload.location,
        registration_url=payload.registration_url,
        related_rfp_id=payload.related_rfp_id,
        description=payload.description,
        source=payload.source,
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return EventRead.model_validate(event)


@router.get("/{event_id}", response_model=EventRead)
async def get_event(
    event_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> EventRead:
    result = await session.execute(
        select(IndustryEvent).where(
            IndustryEvent.id == event_id,
            IndustryEvent.user_id == current_user.id,
        )
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return EventRead.model_validate(event)


@router.patch("/{event_id}", response_model=EventRead)
async def update_event(
    event_id: int,
    payload: EventUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> EventRead:
    result = await session.execute(
        select(IndustryEvent).where(
            IndustryEvent.id == event_id,
            IndustryEvent.user_id == current_user.id,
        )
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)
    event.updated_at = datetime.utcnow()

    await session.commit()
    await session.refresh(event)
    return EventRead.model_validate(event)


@router.delete("/{event_id}")
async def delete_event(
    event_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(
        select(IndustryEvent).where(
            IndustryEvent.id == event_id,
            IndustryEvent.user_id == current_user.id,
        )
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    await session.delete(event)
    await session.commit()
    return {"message": "Event deleted"}
