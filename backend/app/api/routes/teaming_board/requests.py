"""Teaming Board - Teaming Requests and related endpoints."""

import csv
from datetime import datetime, timedelta
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.capture import (
    TeamingDigestChannel,
    TeamingDigestFrequency,
    TeamingDigestSchedule,
    TeamingPartner,
    TeamingRequest,
    TeamingRequestStatus,
)
from app.models.user import User
from app.schemas.teaming import (
    PartnerTrendDrilldownRead,
    TeamingCohortDrilldownRead,
    TeamingDigestScheduleUpdate,
    TeamingPartnerCohortDrilldownResponse,
    TeamingPartnerTrendDrilldownResponse,
    TeamingRequestCreate,
    TeamingRequestRead,
    TeamingRequestTrendPointRead,
    TeamingRequestTrendRead,
    TeamingRequestUpdate,
)
from app.services.audit_service import log_audit_event
from app.services.auth_service import UserAuth

from .helpers import (
    TeamingDigestScheduleRead,
    _parse_teaming_channel,
    _parse_teaming_frequency,
    _serialize_teaming_digest_schedule,
)

router = APIRouter()


@router.post("/requests", response_model=TeamingRequestRead)
async def send_teaming_request(
    payload: TeamingRequestCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TeamingRequestRead:
    """Send a teaming request to a public partner."""
    # Verify partner exists and is public
    partner_result = await session.execute(
        select(TeamingPartner).where(
            TeamingPartner.id == payload.to_partner_id,
            TeamingPartner.is_public == True,  # noqa: E712
        )
    )
    partner = partner_result.scalar_one_or_none()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found or not public")

    # Check for duplicate pending request
    existing = await session.execute(
        select(TeamingRequest).where(
            TeamingRequest.from_user_id == current_user.id,
            TeamingRequest.to_partner_id == payload.to_partner_id,
            TeamingRequest.status == TeamingRequestStatus.PENDING,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Pending request already exists")

    request = TeamingRequest(
        from_user_id=current_user.id,
        to_partner_id=payload.to_partner_id,
        rfp_id=payload.rfp_id,
        message=payload.message,
    )
    session.add(request)
    await session.flush()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="teaming_request",
        entity_id=request.id,
        action="teaming.request_sent",
        metadata={"to_partner_id": payload.to_partner_id},
    )
    await session.commit()
    await session.refresh(request)
    sender = await session.get(User, request.from_user_id)

    return TeamingRequestRead(
        id=request.id,
        from_user_id=request.from_user_id,
        from_user_name=sender.full_name if sender else None,
        from_user_email=sender.email if sender else current_user.email,
        to_partner_id=request.to_partner_id,
        rfp_id=request.rfp_id,
        message=request.message,
        status=request.status.value,
        partner_name=partner.name,
        created_at=request.created_at,
        updated_at=request.updated_at,
    )


@router.get("/requests", response_model=list[TeamingRequestRead])
async def list_teaming_requests(
    direction: str = Query("sent", description="'sent' or 'received'"),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[TeamingRequestRead]:
    """List sent or received teaming requests."""
    if direction == "received":
        # Requests to partners owned by current user
        my_partner_result = await session.execute(
            select(TeamingPartner.id).where(TeamingPartner.user_id == current_user.id)
        )
        my_partner_ids = [pid for pid in my_partner_result.scalars().all()]

        if not my_partner_ids:
            return []

        result = await session.execute(
            select(TeamingRequest).where(TeamingRequest.to_partner_id.in_(my_partner_ids))
        )
    else:
        result = await session.execute(
            select(TeamingRequest).where(TeamingRequest.from_user_id == current_user.id)
        )

    requests = result.scalars().all()

    # Fetch partner names
    partner_ids = list({r.to_partner_id for r in requests})
    if partner_ids:
        partners_result = await session.execute(
            select(TeamingPartner).where(TeamingPartner.id.in_(partner_ids))
        )
        partner_map = {p.id: p.name for p in partners_result.scalars().all()}
    else:
        partner_map = {}

    sender_ids = list({r.from_user_id for r in requests})
    if sender_ids:
        senders_result = await session.execute(select(User).where(User.id.in_(sender_ids)))
        sender_map = {
            sender.id: {"name": sender.full_name, "email": sender.email}
            for sender in senders_result.scalars().all()
        }
    else:
        sender_map = {}

    return [
        TeamingRequestRead(
            id=r.id,
            from_user_id=r.from_user_id,
            from_user_name=sender_map.get(r.from_user_id, {}).get("name"),
            from_user_email=sender_map.get(r.from_user_id, {}).get("email"),
            to_partner_id=r.to_partner_id,
            rfp_id=r.rfp_id,
            message=r.message,
            status=r.status.value if isinstance(r.status, TeamingRequestStatus) else r.status,
            partner_name=partner_map.get(r.to_partner_id),
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in requests
    ]


@router.get("/requests/fit-trends", response_model=TeamingRequestTrendRead)
async def get_request_fit_trends(
    days: int = Query(30, ge=7, le=90),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TeamingRequestTrendRead:
    """Daily partner-fit trend view based on sent request outcomes."""
    result = await session.execute(
        select(TeamingRequest).where(TeamingRequest.from_user_id == current_user.id)
    )
    requests = result.scalars().all()

    now = datetime.utcnow()
    window_start = (now - timedelta(days=days - 1)).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    buckets: dict[str, dict[str, int]] = {}
    for offset in range(days):
        day = (window_start + timedelta(days=offset)).date().isoformat()
        buckets[day] = {
            "sent_count": 0,
            "accepted_count": 0,
            "declined_count": 0,
        }

    total_sent = 0
    accepted_count = 0
    declined_count = 0
    pending_count = 0

    for request in requests:
        if request.created_at < window_start:
            continue
        day = request.created_at.date().isoformat()
        if day not in buckets:
            continue

        status = (
            request.status.value
            if isinstance(request.status, TeamingRequestStatus)
            else request.status
        )
        buckets[day]["sent_count"] += 1
        total_sent += 1
        if status == TeamingRequestStatus.ACCEPTED.value:
            buckets[day]["accepted_count"] += 1
            accepted_count += 1
        elif status == TeamingRequestStatus.DECLINED.value:
            buckets[day]["declined_count"] += 1
            declined_count += 1
        else:
            pending_count += 1

    acceptance_rate = round((accepted_count / total_sent) * 100, 2) if total_sent else 0.0
    points: list[TeamingRequestTrendPointRead] = []
    for day, bucket in buckets.items():
        day_sent = bucket["sent_count"]
        fit_score = round((bucket["accepted_count"] / day_sent) * 100, 2) if day_sent else 0.0
        points.append(
            TeamingRequestTrendPointRead(
                date=day,
                sent_count=day_sent,
                accepted_count=bucket["accepted_count"],
                declined_count=bucket["declined_count"],
                fit_score=fit_score,
            )
        )

    return TeamingRequestTrendRead(
        days=days,
        total_sent=total_sent,
        accepted_count=accepted_count,
        declined_count=declined_count,
        pending_count=pending_count,
        acceptance_rate=acceptance_rate,
        points=points,
    )


@router.get(
    "/requests/partner-trends",
    response_model=TeamingPartnerTrendDrilldownResponse,
)
async def get_partner_request_trends(
    days: int = Query(30, ge=7, le=90),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TeamingPartnerTrendDrilldownResponse:
    """Partner-level sent-request trend drilldown for teaming performance reviews."""
    result = await session.execute(
        select(TeamingRequest).where(TeamingRequest.from_user_id == current_user.id)
    )
    requests = result.scalars().all()
    window_start = datetime.utcnow() - timedelta(days=days)

    partner_ids = list(
        {request.to_partner_id for request in requests if request.created_at >= window_start}
    )
    partner_map: dict[int, str] = {}
    if partner_ids:
        partners_result = await session.execute(
            select(TeamingPartner).where(TeamingPartner.id.in_(partner_ids))
        )
        partner_map = {partner.id: partner.name for partner in partners_result.scalars().all()}

    aggregate: dict[int, dict[str, float | int | list[float]]] = {}
    for request in requests:
        if request.created_at < window_start:
            continue
        bucket = aggregate.setdefault(
            request.to_partner_id,
            {
                "sent_count": 0,
                "accepted_count": 0,
                "declined_count": 0,
                "pending_count": 0,
                "response_durations": [],
            },
        )
        bucket["sent_count"] += 1
        status = (
            request.status.value
            if isinstance(request.status, TeamingRequestStatus)
            else request.status
        )
        if status == TeamingRequestStatus.ACCEPTED.value:
            bucket["accepted_count"] += 1
        elif status == TeamingRequestStatus.DECLINED.value:
            bucket["declined_count"] += 1
        else:
            bucket["pending_count"] += 1

        if status in (
            TeamingRequestStatus.ACCEPTED.value,
            TeamingRequestStatus.DECLINED.value,
        ):
            response_hours = max(
                (request.updated_at - request.created_at).total_seconds() / 3600,
                0.0,
            )
            bucket["response_durations"].append(response_hours)

    partners: list[PartnerTrendDrilldownRead] = []
    for partner_id, bucket in aggregate.items():
        sent_count = int(bucket["sent_count"])
        accepted_count = int(bucket["accepted_count"])
        declined_count = int(bucket["declined_count"])
        pending_count = int(bucket["pending_count"])
        acceptance_rate = round((accepted_count / sent_count) * 100, 2) if sent_count else 0.0
        response_durations = bucket["response_durations"]
        avg_response_hours = (
            round(sum(response_durations) / len(response_durations), 2)
            if response_durations
            else None
        )
        partners.append(
            PartnerTrendDrilldownRead(
                partner_id=partner_id,
                partner_name=partner_map.get(partner_id, f"Partner #{partner_id}"),
                sent_count=sent_count,
                accepted_count=accepted_count,
                declined_count=declined_count,
                pending_count=pending_count,
                acceptance_rate=acceptance_rate,
                avg_response_hours=avg_response_hours,
            )
        )
    partners.sort(
        key=lambda item: (item.acceptance_rate, item.sent_count),
        reverse=True,
    )
    return TeamingPartnerTrendDrilldownResponse(days=days, partners=partners)


@router.get(
    "/requests/partner-cohorts",
    response_model=TeamingPartnerCohortDrilldownResponse,
)
async def get_partner_request_cohorts(
    days: int = Query(30, ge=7, le=90),
    top_n: int = Query(8, ge=1, le=25),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TeamingPartnerCohortDrilldownResponse:
    """Cohort drilldowns by partner NAICS and set-aside profile."""
    result = await session.execute(
        select(TeamingRequest).where(TeamingRequest.from_user_id == current_user.id)
    )
    requests = result.scalars().all()
    window_start = datetime.utcnow() - timedelta(days=days)

    filtered_requests = [request for request in requests if request.created_at >= window_start]
    partner_ids = list({request.to_partner_id for request in filtered_requests})

    partner_map: dict[int, TeamingPartner] = {}
    if partner_ids:
        partners_result = await session.execute(
            select(TeamingPartner).where(TeamingPartner.id.in_(partner_ids))
        )
        partner_map = {partner.id: partner for partner in partners_result.scalars().all()}

    def empty_bucket() -> dict[str, int | set[int]]:
        return {
            "partner_ids": set(),
            "sent_count": 0,
            "accepted_count": 0,
            "declined_count": 0,
            "pending_count": 0,
        }

    naics_aggregate: dict[str, dict[str, int | set[int]]] = {}
    set_aside_aggregate: dict[str, dict[str, int | set[int]]] = {}

    for request in filtered_requests:
        partner = partner_map.get(request.to_partner_id)
        if not partner:
            continue
        status = (
            request.status.value
            if isinstance(request.status, TeamingRequestStatus)
            else request.status
        )
        naics_values = sorted(set(partner.naics_codes or [])) or ["unspecified"]
        set_aside_values = sorted(set(partner.set_asides or [])) or ["unspecified"]

        def update_bucket(
            bucket: dict[str, int | set[int]], partner_id: int, request_status: str
        ) -> None:
            partner_ids_bucket = bucket["partner_ids"]
            if isinstance(partner_ids_bucket, set):
                partner_ids_bucket.add(partner_id)
            bucket["sent_count"] = int(bucket["sent_count"]) + 1
            if request_status == TeamingRequestStatus.ACCEPTED.value:
                bucket["accepted_count"] = int(bucket["accepted_count"]) + 1
            elif request_status == TeamingRequestStatus.DECLINED.value:
                bucket["declined_count"] = int(bucket["declined_count"]) + 1
            else:
                bucket["pending_count"] = int(bucket["pending_count"]) + 1

        for naics_value in naics_values:
            bucket = naics_aggregate.setdefault(naics_value, empty_bucket())
            update_bucket(bucket, partner.id, status)
        for set_aside_value in set_aside_values:
            bucket = set_aside_aggregate.setdefault(set_aside_value, empty_bucket())
            update_bucket(bucket, partner.id, status)

    def serialize(
        aggregate: dict[str, dict[str, int | set[int]]],
    ) -> list[TeamingCohortDrilldownRead]:
        rows: list[TeamingCohortDrilldownRead] = []
        for cohort_value, bucket in aggregate.items():
            sent_count = int(bucket["sent_count"])
            accepted_count = int(bucket["accepted_count"])
            declined_count = int(bucket["declined_count"])
            pending_count = int(bucket["pending_count"])
            acceptance_rate = round((accepted_count / sent_count) * 100, 2) if sent_count else 0.0
            partner_count = (
                len(bucket["partner_ids"]) if isinstance(bucket["partner_ids"], set) else 0
            )
            rows.append(
                TeamingCohortDrilldownRead(
                    cohort_value=cohort_value,
                    partner_count=partner_count,
                    sent_count=sent_count,
                    accepted_count=accepted_count,
                    declined_count=declined_count,
                    pending_count=pending_count,
                    acceptance_rate=acceptance_rate,
                )
            )
        rows.sort(
            key=lambda row: (
                -row.sent_count,
                -row.acceptance_rate,
                -row.partner_count,
                row.cohort_value == "unspecified",
                row.cohort_value,
            )
        )
        return rows[:top_n]

    return TeamingPartnerCohortDrilldownResponse(
        days=days,
        total_sent=len(filtered_requests),
        naics_cohorts=serialize(naics_aggregate),
        set_aside_cohorts=serialize(set_aside_aggregate),
    )


@router.get("/digest-schedule", response_model=TeamingDigestScheduleRead)
async def get_teaming_digest_schedule(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TeamingDigestScheduleRead:
    """Get (or create default) teaming digest schedule for current user."""
    schedule = (
        await session.execute(
            select(TeamingDigestSchedule).where(TeamingDigestSchedule.user_id == current_user.id)
        )
    ).scalar_one_or_none()
    if not schedule:
        schedule = TeamingDigestSchedule(
            user_id=current_user.id,
            frequency=TeamingDigestFrequency.WEEKLY,
            day_of_week=1,
            hour_utc=14,
            minute_utc=0,
            channel=TeamingDigestChannel.IN_APP,
            include_declined_reasons=True,
            is_enabled=True,
        )
        session.add(schedule)
        await session.commit()
        await session.refresh(schedule)
    return _serialize_teaming_digest_schedule(schedule)


@router.patch("/digest-schedule", response_model=TeamingDigestScheduleRead)
async def update_teaming_digest_schedule(
    payload: TeamingDigestScheduleUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TeamingDigestScheduleRead:
    """Update teaming performance digest delivery preferences."""
    if payload.day_of_week is not None and not (0 <= payload.day_of_week <= 6):
        raise HTTPException(400, "day_of_week must be between 0 and 6")
    if payload.hour_utc < 0 or payload.hour_utc > 23:
        raise HTTPException(400, "hour_utc must be between 0 and 23")
    if payload.minute_utc < 0 or payload.minute_utc > 59:
        raise HTTPException(400, "minute_utc must be between 0 and 59")

    schedule = (
        await session.execute(
            select(TeamingDigestSchedule).where(TeamingDigestSchedule.user_id == current_user.id)
        )
    ).scalar_one_or_none()
    if not schedule:
        schedule = TeamingDigestSchedule(user_id=current_user.id)

    schedule.frequency = _parse_teaming_frequency(payload.frequency)
    schedule.day_of_week = payload.day_of_week
    schedule.hour_utc = payload.hour_utc
    schedule.minute_utc = payload.minute_utc
    schedule.channel = _parse_teaming_channel(payload.channel)
    schedule.include_declined_reasons = payload.include_declined_reasons
    schedule.is_enabled = payload.is_enabled
    schedule.updated_at = datetime.utcnow()
    session.add(schedule)
    await session.commit()
    await session.refresh(schedule)
    return _serialize_teaming_digest_schedule(schedule)


@router.post("/digest-send")
async def send_teaming_digest(
    days: int = Query(30, ge=7, le=90),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Simulate digest delivery and return latest teaming performance snapshot."""
    schedule = (
        await session.execute(
            select(TeamingDigestSchedule).where(TeamingDigestSchedule.user_id == current_user.id)
        )
    ).scalar_one_or_none()
    if not schedule:
        schedule = TeamingDigestSchedule(user_id=current_user.id)
        session.add(schedule)
        await session.commit()
        await session.refresh(schedule)
    if not schedule.is_enabled:
        raise HTTPException(400, "Teaming digest schedule is disabled")

    trends = await get_request_fit_trends(
        days=days,
        current_user=current_user,
        session=session,
    )
    partner_trends = await get_partner_request_trends(
        days=days,
        current_user=current_user,
        session=session,
    )
    top_partners = partner_trends.partners[:5]
    digest_items = [
        {
            "partner_id": item.partner_id,
            "partner_name": item.partner_name,
            "sent_count": item.sent_count,
            "accepted_count": item.accepted_count,
            "declined_count": item.declined_count,
            "acceptance_rate": item.acceptance_rate,
            "avg_response_hours": item.avg_response_hours,
        }
        for item in top_partners
    ]
    if not schedule.include_declined_reasons:
        for item in digest_items:
            item.pop("declined_count", None)

    schedule.last_sent_at = datetime.utcnow()
    schedule.updated_at = datetime.utcnow()
    session.add(schedule)
    await session.commit()
    await session.refresh(schedule)

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "period_days": days,
        "schedule": _serialize_teaming_digest_schedule(schedule).model_dump(),
        "summary": {
            "total_sent": trends.total_sent,
            "accepted_count": trends.accepted_count,
            "declined_count": trends.declined_count,
            "pending_count": trends.pending_count,
            "acceptance_rate": trends.acceptance_rate,
        },
        "top_partners": digest_items,
    }


@router.get("/requests/audit-export")
async def export_requests_audit(
    direction: str = Query("all", pattern="^(sent|received|all)$"),
    days: int = Query(30, ge=1, le=365),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """Export sent/received request timeline events for audit reviews."""
    my_partner_result = await session.execute(
        select(TeamingPartner.id).where(TeamingPartner.user_id == current_user.id)
    )
    my_partner_ids = [partner_id for partner_id in my_partner_result.scalars().all()]

    query = select(TeamingRequest)
    if direction == "sent":
        query = query.where(TeamingRequest.from_user_id == current_user.id)
    elif direction == "received":
        if not my_partner_ids:
            query = query.where(TeamingRequest.id == -1)
        else:
            query = query.where(TeamingRequest.to_partner_id.in_(my_partner_ids))
    else:
        if my_partner_ids:
            query = query.where(
                (TeamingRequest.from_user_id == current_user.id)
                | (TeamingRequest.to_partner_id.in_(my_partner_ids))
            )
        else:
            query = query.where(TeamingRequest.from_user_id == current_user.id)

    result = await session.execute(query)
    requests = result.scalars().all()

    partner_ids = list({request.to_partner_id for request in requests})
    partners_result = await session.execute(
        select(TeamingPartner).where(TeamingPartner.id.in_(partner_ids))
    )
    partner_map = {partner.id: partner.name for partner in partners_result.scalars().all()}

    sender_ids = list({request.from_user_id for request in requests})
    sender_result = await session.execute(select(User).where(User.id.in_(sender_ids)))
    sender_map = {sender.id: sender for sender in sender_result.scalars().all()}

    now = datetime.utcnow()
    window_start = now - timedelta(days=days)

    events: list[dict[str, str | int | None]] = []

    def add_event(
        request: TeamingRequest,
        event_type: str,
        event_time: datetime,
    ) -> None:
        if event_time < window_start:
            return
        sender = sender_map.get(request.from_user_id)
        events.append(
            {
                "request_id": request.id,
                "event_type": event_type,
                "event_timestamp": event_time.isoformat(),
                "direction": "sent" if request.from_user_id == current_user.id else "received",
                "status": (
                    request.status.value
                    if isinstance(request.status, TeamingRequestStatus)
                    else request.status
                ),
                "partner_id": request.to_partner_id,
                "partner_name": partner_map.get(request.to_partner_id),
                "from_user_id": request.from_user_id,
                "from_user_name": sender.full_name if sender else None,
                "from_user_email": sender.email if sender else None,
                "rfp_id": request.rfp_id,
                "message": request.message,
            }
        )

    for request in requests:
        add_event(request, "request_sent", request.created_at)
        status = (
            request.status.value
            if isinstance(request.status, TeamingRequestStatus)
            else request.status
        )
        if status != TeamingRequestStatus.PENDING.value:
            add_event(request, f"request_{status}", request.updated_at)

    events.sort(key=lambda event: str(event["event_timestamp"]), reverse=True)

    output = StringIO()
    headers = [
        "request_id",
        "event_type",
        "event_timestamp",
        "direction",
        "status",
        "partner_id",
        "partner_name",
        "from_user_id",
        "from_user_name",
        "from_user_email",
        "rfp_id",
        "message",
    ]
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    writer.writerows(events)

    response = StreamingResponse(iter([output.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = (
        f'attachment; filename="teaming_requests_audit_{now.strftime("%Y%m%d")}.csv"'
    )
    return response


@router.patch("/requests/{request_id}", response_model=TeamingRequestRead)
async def update_teaming_request(
    request_id: int,
    payload: TeamingRequestUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TeamingRequestRead:
    """Accept or decline a teaming request (must own the target partner)."""
    if payload.status not in ("accepted", "declined"):
        raise HTTPException(status_code=400, detail="Status must be 'accepted' or 'declined'")

    result = await session.execute(select(TeamingRequest).where(TeamingRequest.id == request_id))
    request = result.scalar_one_or_none()
    if not request:
        raise HTTPException(status_code=404, detail="Teaming request not found")

    # Verify current user owns the target partner
    partner_result = await session.execute(
        select(TeamingPartner).where(
            TeamingPartner.id == request.to_partner_id,
            TeamingPartner.user_id == current_user.id,
        )
    )
    partner = partner_result.scalar_one_or_none()
    if not partner:
        raise HTTPException(status_code=403, detail="Not authorized to update this request")

    request.status = TeamingRequestStatus(payload.status)
    request.updated_at = datetime.utcnow()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="teaming_request",
        entity_id=request.id,
        action=f"teaming.request_{payload.status}",
        metadata={"from_user_id": request.from_user_id},
    )
    await session.commit()
    await session.refresh(request)
    sender = await session.get(User, request.from_user_id)

    return TeamingRequestRead(
        id=request.id,
        from_user_id=request.from_user_id,
        from_user_name=sender.full_name if sender else None,
        from_user_email=sender.email if sender else None,
        to_partner_id=request.to_partner_id,
        rfp_id=request.rfp_id,
        message=request.message,
        status=request.status.value
        if isinstance(request.status, TeamingRequestStatus)
        else request.status,
        partner_name=partner.name,
        created_at=request.created_at,
        updated_at=request.updated_at,
    )
