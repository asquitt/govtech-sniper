"""Market signals feed and subscription routes."""

from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Any, Optional
from xml.etree import ElementTree

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.budget_intel import BudgetIntelligence
from app.models.market_signal import MarketSignal, SignalSubscription, SignalType
from app.schemas.signal import (
    SignalCreate,
    SignalDigestPreview,
    SignalDigestSendResponse,
    SignalIngestResponse,
    SignalListResponse,
    SignalRead,
    SignalRescoreResponse,
    SubscriptionCreate,
    SubscriptionRead,
)
from app.services.audit_service import log_audit_event
from app.services.auth_service import UserAuth

router = APIRouter(prefix="/signals", tags=["Signals"])

CURATED_NEWS_SOURCES: tuple[tuple[str, str], ...] = (
    ("federal_news_network", "https://federalnewsnetwork.com/category/acquisition-policy/feed/"),
    ("gao_reports", "https://www.gao.gov/reports-testimonies/rss"),
)


def _normalize_text(value: str | None) -> str:
    return (value or "").strip().lower()


def _parse_rss_date(raw_value: str | None) -> datetime | None:
    if not raw_value:
        return None
    try:
        parsed = parsedate_to_datetime(raw_value)
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(tz=None).replace(tzinfo=None)
        return parsed
    except (TypeError, ValueError):
        return None


async def _fetch_news_from_source(source: str, url: str, limit: int) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
    root = ElementTree.fromstring(response.text)
    items = root.findall(".//item")
    output: list[dict[str, Any]] = []
    for item in items[:limit]:
        title = item.findtext("title")
        link = item.findtext("link")
        description = item.findtext("description")
        pub_date = _parse_rss_date(item.findtext("pubDate"))
        if not title:
            continue
        output.append(
            {
                "title": title.strip(),
                "agency": None,
                "content": (description or "").strip()[:1500] or None,
                "source_url": (link or "").strip() or None,
                "published_at": pub_date,
                "source": source,
            }
        )
    return output


def _fallback_news(now: datetime) -> list[dict[str, Any]]:
    month_label = now.strftime("%B %Y")
    return [
        {
            "title": f"DoD acquisition modernization priorities ({month_label})",
            "agency": "Department of Defense",
            "content": (
                "Curated summary of defense acquisition policy updates focused on "
                "software modernization, cyber resilience, and rapid contracting."
            ),
            "source_url": "https://www.acq.osd.mil/",
            "published_at": now - timedelta(hours=6),
            "source": "fallback:dod-acquisition",
        },
        {
            "title": f"VA cloud services recompete watchlist ({month_label})",
            "agency": "Department of Veterans Affairs",
            "content": (
                "Curated watchlist highlighting VA cloud and digital services recompetes "
                "with expected pre-solicitation activity."
            ),
            "source_url": "https://www.va.gov/oal/business/",
            "published_at": now - timedelta(hours=12),
            "source": "fallback:va-business",
        },
    ]


def _score_signal(
    title: str,
    content: str | None,
    agency: str | None,
    signal_type: SignalType,
    subscription: SignalSubscription | None,
) -> float:
    score = 15.0
    haystack = f"{title} {content or ''}".lower()
    if signal_type == SignalType.BUDGET:
        score += 8
    if signal_type == SignalType.RECOMPETE:
        score += 6
    if not subscription:
        return round(min(100.0, score), 1)

    normalized_agency = _normalize_text(agency)
    for tracked_agency in subscription.agencies:
        agency_term = _normalize_text(tracked_agency)
        if not agency_term:
            continue
        if agency_term in normalized_agency or agency_term in haystack:
            score += 34
            break

    keyword_hits = [
        keyword
        for keyword in subscription.keywords
        if _normalize_text(keyword) and _normalize_text(keyword) in haystack
    ]
    if keyword_hits:
        score += min(30.0, len(keyword_hits) * 9.0)

    naics_hits = [
        code
        for code in subscription.naics_codes
        if _normalize_text(code) and _normalize_text(code) in haystack
    ]
    if naics_hits:
        score += min(20.0, len(naics_hits) * 8.0)

    return round(min(100.0, score), 1)


async def _get_subscription(
    session: AsyncSession,
    user_id: int,
) -> SignalSubscription | None:
    result = await session.execute(
        select(SignalSubscription).where(SignalSubscription.user_id == user_id)
    )
    return result.scalar_one_or_none()


def _build_digest_preview(
    signals: list[MarketSignal],
    period_days: int,
) -> SignalDigestPreview:
    type_breakdown: dict[str, int] = {}
    for signal in signals:
        type_breakdown[signal.signal_type.value] = (
            type_breakdown.get(signal.signal_type.value, 0) + 1
        )
    top_signals = [
        {
            "signal_id": signal.id,
            "title": signal.title,
            "signal_type": signal.signal_type,
            "agency": signal.agency,
            "relevance_score": signal.relevance_score,
            "source_url": signal.source_url,
            "published_at": signal.published_at,
        }
        for signal in signals[:10]
    ]
    return SignalDigestPreview(
        period_days=period_days,
        total_unread=len(signals),
        included_count=len(top_signals),
        type_breakdown=type_breakdown,
        top_signals=top_signals,
    )


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
    subscription = await _get_subscription(session, current_user.id)
    computed_score = (
        payload.relevance_score
        if payload.relevance_score > 0
        else _score_signal(
            title=payload.title,
            content=payload.content,
            agency=payload.agency,
            signal_type=payload.signal_type,
            subscription=subscription,
        )
    )
    signal = MarketSignal(
        user_id=current_user.id,
        title=payload.title,
        signal_type=payload.signal_type,
        agency=payload.agency,
        content=payload.content,
        source_url=payload.source_url,
        relevance_score=computed_score,
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


@router.post("/ingest/news", response_model=SignalIngestResponse)
async def ingest_news_signals(
    max_items_per_source: int = Query(default=8, ge=1, le=25),
    use_fallback_only: bool = Query(default=False),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SignalIngestResponse:
    """Ingest news signals from curated government contracting sources."""
    now = datetime.utcnow()
    subscription = await _get_subscription(session, current_user.id)
    existing_result = await session.execute(
        select(MarketSignal).where(MarketSignal.user_id == current_user.id)
    )
    existing = existing_result.scalars().all()
    existing_by_url = {signal.source_url for signal in existing if signal.source_url}
    existing_by_title = {signal.title.lower().strip() for signal in existing}

    candidates: list[dict[str, Any]] = []
    source_breakdown: dict[str, int] = {}
    if not use_fallback_only:
        for source_name, url in CURATED_NEWS_SOURCES:
            try:
                source_items = await _fetch_news_from_source(source_name, url, max_items_per_source)
            except (httpx.HTTPError, ElementTree.ParseError):
                source_items = []
            if source_items:
                candidates.extend(source_items)
                source_breakdown[source_name] = len(source_items)

    if not candidates:
        fallback_items = _fallback_news(now)
        candidates.extend(fallback_items)
        source_breakdown["fallback"] = len(fallback_items)

    created = 0
    skipped = 0
    for item in candidates:
        source_url = item.get("source_url")
        title = str(item["title"]).strip()
        if (source_url and source_url in existing_by_url) or title.lower() in existing_by_title:
            skipped += 1
            continue
        score = _score_signal(
            title=title,
            content=item.get("content"),
            agency=item.get("agency"),
            signal_type=SignalType.NEWS,
            subscription=subscription,
        )
        signal = MarketSignal(
            user_id=current_user.id,
            title=title,
            signal_type=SignalType.NEWS,
            agency=item.get("agency"),
            content=item.get("content"),
            source_url=source_url,
            relevance_score=score,
            published_at=item.get("published_at"),
        )
        session.add(signal)
        created += 1
        if source_url:
            existing_by_url.add(source_url)
        existing_by_title.add(title.lower())

    await session.commit()
    return SignalIngestResponse(
        created=created,
        skipped=skipped,
        source_breakdown=source_breakdown,
    )


@router.post("/ingest/budget-analysis", response_model=SignalIngestResponse)
async def ingest_budget_signals(
    limit: int = Query(default=25, ge=1, le=200),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SignalIngestResponse:
    """Generate budget-intelligence signals from budget documents and notes."""
    subscription = await _get_subscription(session, current_user.id)
    records_result = await session.execute(
        select(BudgetIntelligence)
        .where(BudgetIntelligence.user_id == current_user.id)
        .order_by(BudgetIntelligence.updated_at.desc())
        .limit(limit)
    )
    records = records_result.scalars().all()

    existing_result = await session.execute(
        select(MarketSignal).where(
            MarketSignal.user_id == current_user.id,
            MarketSignal.signal_type == SignalType.BUDGET,
        )
    )
    existing_titles = {signal.title.lower().strip() for signal in existing_result.scalars().all()}

    created = 0
    skipped = 0
    for record in records:
        title = f"Budget Insight: {record.title}".strip()[:255]
        if title.lower() in existing_titles:
            skipped += 1
            continue
        summary_parts = []
        if record.fiscal_year:
            summary_parts.append(f"Fiscal year {record.fiscal_year}.")
        if record.amount is not None:
            summary_parts.append(f"Tracked budget amount: ${record.amount:,.0f}.")
        if record.notes:
            summary_parts.append(record.notes.strip())
        if not summary_parts:
            summary_parts.append("Budget signal synthesized from tracked budget document metadata.")
        content = " ".join(summary_parts)[:1500]
        score = _score_signal(
            title=title,
            content=content,
            agency=None,
            signal_type=SignalType.BUDGET,
            subscription=subscription,
        )
        signal = MarketSignal(
            user_id=current_user.id,
            title=title,
            signal_type=SignalType.BUDGET,
            agency=None,
            content=content,
            source_url=record.source_url,
            relevance_score=score,
            published_at=record.updated_at,
        )
        session.add(signal)
        existing_titles.add(title.lower())
        created += 1

    await session.commit()
    return SignalIngestResponse(
        created=created,
        skipped=skipped,
        source_breakdown={"budget_intelligence": len(records)},
    )


@router.post("/rescore", response_model=SignalRescoreResponse)
async def rescore_signals(
    unread_only: bool = Query(default=False),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SignalRescoreResponse:
    """Recalculate relevance scores using the latest subscription profile."""
    subscription = await _get_subscription(session, current_user.id)
    query = select(MarketSignal).where(MarketSignal.user_id == current_user.id)
    if unread_only:
        query = query.where(MarketSignal.is_read == False)
    result = await session.execute(query)
    signals = result.scalars().all()

    if not signals:
        return SignalRescoreResponse(updated=0, average_score=0.0)

    total = 0.0
    for signal in signals:
        next_score = _score_signal(
            title=signal.title,
            content=signal.content,
            agency=signal.agency,
            signal_type=signal.signal_type,
            subscription=subscription,
        )
        signal.relevance_score = next_score
        total += next_score

    await session.commit()
    return SignalRescoreResponse(
        updated=len(signals),
        average_score=round(total / len(signals), 2),
    )


@router.get("/digest-preview", response_model=SignalDigestPreview)
async def signal_digest_preview(
    period_days: int = Query(default=1, ge=1, le=30),
    limit: int = Query(default=25, ge=1, le=100),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SignalDigestPreview:
    """Preview the next market-signals digest payload."""
    cutoff = datetime.utcnow() - timedelta(days=period_days)
    result = await session.execute(
        select(MarketSignal)
        .where(
            MarketSignal.user_id == current_user.id,
            MarketSignal.is_read == False,
            MarketSignal.created_at >= cutoff,
        )
        .order_by(MarketSignal.relevance_score.desc(), MarketSignal.created_at.desc())
        .limit(limit)
    )
    signals = result.scalars().all()
    return _build_digest_preview(signals, period_days)


@router.post("/digest-send", response_model=SignalDigestSendResponse)
async def send_signal_digest(
    period_days: int = Query(default=1, ge=1, le=30),
    limit: int = Query(default=25, ge=1, le=100),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SignalDigestSendResponse:
    """Simulate digest email delivery and return the payload sent to the user."""
    subscription = await _get_subscription(session, current_user.id)
    if not subscription or not subscription.email_digest_enabled:
        raise HTTPException(status_code=400, detail="Signal digest is disabled")

    preview = await signal_digest_preview(
        period_days=period_days,
        limit=limit,
        current_user=current_user,
        session=session,
    )

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="signal_digest",
        entity_id=0,
        action="signals.digest.sent",
        metadata={
            "period_days": period_days,
            "included_count": preview.included_count,
            "frequency": subscription.digest_frequency.value,
        },
    )
    await session.commit()

    return SignalDigestSendResponse(
        **preview.model_dump(),
        recipient_email=current_user.email,
        sent_at=datetime.utcnow(),
        simulated=True,
    )
