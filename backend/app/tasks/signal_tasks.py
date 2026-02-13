"""
RFP Sniper - Signal Tasks
===========================
Celery tasks for polling RSS feeds and sending signal digests.
"""

import asyncio
from datetime import datetime, timedelta

import structlog
from sqlmodel import select

from app.database import get_celery_session_context
from app.models.market_signal import MarketSignal, SignalSubscription
from app.services.signal_feeds import RSS_FEED_REGISTRY, fetch_feed, score_relevance
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)

RELEVANCE_THRESHOLD = 0.2


def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.tasks.signal_tasks.poll_signal_feeds")
def poll_signal_feeds() -> dict:
    """Fetch RSS feeds and create MarketSignal records for relevant entries."""

    async def _poll() -> dict:
        created = 0
        feeds_polled = 0

        async with get_celery_session_context() as session:
            # Get all subscriptions
            sub_result = await session.execute(select(SignalSubscription))
            subscriptions = sub_result.scalars().all()

            if not subscriptions:
                return {"created": 0, "feeds_polled": 0, "reason": "no_subscriptions"}

            for feed_config in RSS_FEED_REGISTRY:
                entries = fetch_feed(feed_config)
                feeds_polled += 1

                for entry in entries:
                    for sub in subscriptions:
                        relevance = score_relevance(
                            entry,
                            agencies=sub.agencies or [],
                            naics_codes=sub.naics_codes or [],
                            keywords=sub.keywords or [],
                        )

                        if relevance < RELEVANCE_THRESHOLD:
                            continue

                        # Deduplicate: check if same title+user already exists
                        existing = await session.execute(
                            select(MarketSignal).where(
                                MarketSignal.user_id == sub.user_id,
                                MarketSignal.title == entry["title"],
                            )
                        )
                        if existing.scalar_one_or_none():
                            continue

                        signal = MarketSignal(
                            user_id=sub.user_id,
                            title=entry["title"],
                            signal_type=entry["signal_type"],
                            agency=entry.get("agency"),
                            content=entry.get("content"),
                            source_url=entry.get("source_url"),
                            relevance_score=round(relevance, 3),
                            published_at=entry.get("published_at"),
                        )
                        session.add(signal)
                        created += 1

            await session.commit()

        return {"created": created, "feeds_polled": feeds_polled}

    result = run_async(_poll())
    logger.info("Signal feed poll complete", **result)
    return {"status": "ok", **result}


@celery_app.task(name="app.tasks.signal_tasks.send_signal_digest")
def send_signal_digest() -> dict:
    """Send email digest of unread signals to subscribed users."""
    from app.api.routes.notifications import email_service
    from app.config import settings

    async def _send() -> dict:
        sent = 0

        async with get_celery_session_context() as session:
            sub_result = await session.execute(
                select(SignalSubscription).where(SignalSubscription.email_digest_enabled == True)
            )
            subscriptions = sub_result.scalars().all()

            for sub in subscriptions:
                # Get unread signals from last 24h
                cutoff = datetime.utcnow() - timedelta(days=1)
                signals_result = await session.execute(
                    select(MarketSignal)
                    .where(
                        MarketSignal.user_id == sub.user_id,
                        MarketSignal.is_read == False,
                        MarketSignal.created_at >= cutoff,
                    )
                    .order_by(MarketSignal.relevance_score.desc())
                    .limit(20)
                )
                signals = signals_result.scalars().all()

                if not signals:
                    continue

                # Build digest email
                items_html = ""
                for s in signals:
                    items_html += f"""
                    <div style="border-bottom: 1px solid #eee; padding: 10px 0;">
                        <strong>{s.title}</strong>
                        <br><span style="color: #666;">{s.agency or "N/A"} &middot;
                        {s.signal_type.value} &middot;
                        Score: {s.relevance_score:.0%}</span>
                        {f'<br><a href="{s.source_url}">Source</a>' if s.source_url else ""}
                    </div>
                    """

                html = f"""
                <html>
                <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <div style="background: #1a365d; color: white; padding: 20px; text-align: center;">
                        <h1 style="margin: 0;">RFP Sniper — Market Signals</h1>
                    </div>
                    <div style="padding: 20px;">
                        <h2>Your Daily Signal Digest</h2>
                        <p>{len(signals)} new signal{"s" if len(signals) != 1 else ""} matched
                        your subscription.</p>
                        {items_html}
                        <p style="margin-top: 20px;">
                            <a href="{settings.app_url}/signals"
                               style="background: #3182ce; color: white; padding: 10px 20px;
                                      text-decoration: none; border-radius: 5px;">
                                View All Signals
                            </a>
                        </p>
                    </div>
                    <div style="background: #f7f7f7; padding: 15px; text-align: center;
                                font-size: 12px; color: #666;">
                        <a href="{settings.app_url}/settings/notifications">
                        Manage preferences</a>
                    </div>
                </body>
                </html>
                """

                # Get user email from subscription (need to fetch user)
                from app.models.user import User

                user_result = await session.execute(select(User).where(User.id == sub.user_id))
                user = user_result.scalar_one_or_none()
                if not user or not user.email:
                    continue

                subject = f"RFP Sniper Signal Digest — {len(signals)} new signals"
                await email_service.send_email(user.email, subject, html)
                sent += 1

        return {"sent": sent}

    result = run_async(_send())
    logger.info("Signal digest complete", **result)
    return {"status": "ok", **result}
