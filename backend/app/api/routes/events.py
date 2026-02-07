"""Industry events CRUD and calendar routes."""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.api.deps import get_current_user
from app.services.auth_service import UserAuth
from app.models.event import IndustryEvent
from app.schemas.event import EventCreate, EventUpdate, EventRead, EventListResponse

router = APIRouter(prefix="/events", tags=["Events"])


@router.get("", response_model=List[EventRead])
async def list_events(
    archived: bool = False,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[EventRead]:
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


@router.get("/upcoming", response_model=List[EventRead])
async def upcoming_events(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[EventRead]:
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


@router.get("/calendar", response_model=List[EventRead])
async def calendar_events(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2020, le=2100),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[EventRead]:
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
