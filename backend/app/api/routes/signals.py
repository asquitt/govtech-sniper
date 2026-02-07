"""Market signals feed and subscription routes."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.market_signal import MarketSignal, SignalSubscription, SignalType
from app.schemas.signal import (
    SignalCreate,
    SignalListResponse,
    SignalRead,
    SubscriptionCreate,
    SubscriptionRead,
)
from app.services.auth_service import UserAuth

router = APIRouter(prefix="/signals", tags=["Signals"])


@router.get("/feed", response_model=SignalListResponse)
async def get_signal_feed(
    signal_type: SignalType | None = None,
    agency: str | None = None,
    unread_only: bool = False,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SignalListResponse:
    query = select(MarketSignal).where(MarketSignal.user_id == current_user.id)

    if signal_type:
        query = query.where(MarketSignal.signal_type == signal_type)
    if agency:
        query = query.where(MarketSignal.agency == agency)
    if unread_only:
        query = query.where(MarketSignal.is_read == False)

    # Count total
    from sqlalchemy import func

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    # Fetch page
    query = query.order_by(MarketSignal.relevance_score.desc(), MarketSignal.created_at.desc())
    query = query.offset(offset).limit(limit)
    result = await session.execute(query)
    signals = result.scalars().all()

    return SignalListResponse(
        signals=[SignalRead.model_validate(s) for s in signals],
        total=total,
    )


@router.get("", response_model=list[SignalRead])
async def list_signals(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[SignalRead]:
    result = await session.execute(
        select(MarketSignal)
        .where(MarketSignal.user_id == current_user.id)
        .order_by(MarketSignal.created_at.desc())
        .limit(100)
    )
    signals = result.scalars().all()
    return [SignalRead.model_validate(s) for s in signals]


@router.post("", response_model=SignalRead)
async def create_signal(
    payload: SignalCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SignalRead:
    signal = MarketSignal(
        user_id=current_user.id,
        title=payload.title,
        signal_type=payload.signal_type,
        agency=payload.agency,
        content=payload.content,
        source_url=payload.source_url,
        relevance_score=payload.relevance_score,
        published_at=payload.published_at,
    )
    session.add(signal)
    await session.commit()
    await session.refresh(signal)
    return SignalRead.model_validate(signal)


@router.patch("/{signal_id}/read")
async def mark_signal_read(
    signal_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(
        select(MarketSignal).where(
            MarketSignal.id == signal_id,
            MarketSignal.user_id == current_user.id,
        )
    )
    signal = result.scalar_one_or_none()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    signal.is_read = True
    await session.commit()
    return {"message": "Signal marked as read"}


@router.delete("/{signal_id}")
async def delete_signal(
    signal_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(
        select(MarketSignal).where(
            MarketSignal.id == signal_id,
            MarketSignal.user_id == current_user.id,
        )
    )
    signal = result.scalar_one_or_none()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    await session.delete(signal)
    await session.commit()
    return {"message": "Signal deleted"}


@router.get("/subscription", response_model=Optional[SubscriptionRead])
async def get_subscription(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SubscriptionRead | None:
    result = await session.execute(
        select(SignalSubscription).where(SignalSubscription.user_id == current_user.id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        return None
    return SubscriptionRead.model_validate(sub)


@router.post("/subscription", response_model=SubscriptionRead)
async def upsert_subscription(
    payload: SubscriptionCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SubscriptionRead:
    result = await session.execute(
        select(SignalSubscription).where(SignalSubscription.user_id == current_user.id)
    )
    sub = result.scalar_one_or_none()

    if sub:
        sub.agencies = payload.agencies
        sub.naics_codes = payload.naics_codes
        sub.keywords = payload.keywords
        sub.email_digest_enabled = payload.email_digest_enabled
        sub.digest_frequency = payload.digest_frequency
        sub.updated_at = datetime.utcnow()
    else:
        sub = SignalSubscription(
            user_id=current_user.id,
            agencies=payload.agencies,
            naics_codes=payload.naics_codes,
            keywords=payload.keywords,
            email_digest_enabled=payload.email_digest_enabled,
            digest_frequency=payload.digest_frequency,
        )
        session.add(sub)

    await session.commit()
    await session.refresh(sub)
    return SubscriptionRead.model_validate(sub)
