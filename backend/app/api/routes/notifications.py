"""
RFP Sniper - Notifications Routes
==================================
Email notifications and deadline reminders.
"""

from datetime import datetime, timedelta
from enum import Enum

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import JSON, Column, Field, SQLModel, Text, select

from app.api.deps import UserAuth, get_current_user
from app.config import settings
from app.database import get_session
from app.models.rfp import RFP
from app.models.user import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# =============================================================================
# Notification Models
# =============================================================================


class NotificationType(str, Enum):
    """Types of notifications."""

    DEADLINE_REMINDER = "deadline_reminder"
    RFP_MATCH = "rfp_match"
    ANALYSIS_COMPLETE = "analysis_complete"
    GENERATION_COMPLETE = "generation_complete"
    SYSTEM_ALERT = "system_alert"
    TEAM_INVITE = "team_invite"
    COMMENT_ADDED = "comment_added"


class NotificationChannel(str, Enum):
    """Delivery channels."""

    EMAIL = "email"
    IN_APP = "in_app"
    SLACK = "slack"
    WEBHOOK = "webhook"


class Notification(SQLModel, table=True):
    """
    Notification record.
    """

    __tablename__ = "notifications"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)

    # Notification content
    notification_type: NotificationType
    title: str = Field(max_length=255)
    message: str = Field(sa_column=Column(Text))

    # Delivery
    channels: list[str] = Field(default=["in_app"], sa_column=Column(JSON))
    is_read: bool = Field(default=False)
    is_sent: bool = Field(default=False)
    sent_at: datetime | None = None

    # Related entities
    rfp_id: int | None = Field(default=None, foreign_key="rfps.id")
    proposal_id: int | None = Field(default=None, foreign_key="proposals.id")

    # Metadata
    meta: dict = Field(default={}, sa_column=Column("metadata", JSON))

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)


class NotificationPreferences(SQLModel, table=True):
    """
    User notification preferences.
    """

    __tablename__ = "notification_preferences"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", unique=True)

    # Email preferences
    email_enabled: bool = Field(default=True)
    email_address: str | None = Field(default=None, max_length=255)

    # Notification types
    deadline_reminders: bool = Field(default=True)
    deadline_days_before: list[int] = Field(default=[7, 3, 1], sa_column=Column(JSON))
    rfp_matches: bool = Field(default=True)
    analysis_complete: bool = Field(default=True)
    generation_complete: bool = Field(default=True)
    team_activity: bool = Field(default=True)

    # Slack integration
    slack_enabled: bool = Field(default=False)
    slack_webhook_url: str | None = Field(default=None, max_length=500)

    # Quiet hours (no notifications)
    quiet_hours_enabled: bool = Field(default=False)
    quiet_hours_start: str | None = Field(default=None, max_length=5)  # "22:00"
    quiet_hours_end: str | None = Field(default=None, max_length=5)  # "08:00"

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Request/Response Schemas
# =============================================================================


class NotificationResponse(BaseModel):
    """Notification response."""

    id: int
    notification_type: str
    title: str
    message: str
    is_read: bool
    rfp_id: int | None
    proposal_id: int | None
    created_at: datetime


class PreferencesUpdate(BaseModel):
    """Update notification preferences."""

    email_enabled: bool | None = None
    email_address: EmailStr | None = None
    deadline_reminders: bool | None = None
    deadline_days_before: list[int] | None = None
    rfp_matches: bool | None = None
    analysis_complete: bool | None = None
    generation_complete: bool | None = None
    team_activity: bool | None = None
    slack_enabled: bool | None = None
    slack_webhook_url: str | None = None
    quiet_hours_enabled: bool | None = None
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None


# =============================================================================
# Email Service
# =============================================================================


class EmailService:
    """
    Email sending service.
    In production, integrate with SendGrid, SES, or similar.
    """

    @staticmethod
    async def send_email(
        to_email: str,
        subject: str,
        body_html: str,
        body_text: str = None,
    ) -> bool:
        """
        Send an email.

        For now, this logs the email. Replace with actual email service.
        """
        try:
            # TODO: Replace with actual email service integration
            # Example with SendGrid:
            # import sendgrid
            # from sendgrid.helpers.mail import Mail
            # sg = sendgrid.SendGridAPIClient(api_key=settings.sendgrid_api_key)
            # message = Mail(
            #     from_email=settings.email_from,
            #     to_emails=to_email,
            #     subject=subject,
            #     html_content=body_html,
            # )
            # sg.send(message)

            logger.info(
                "Email sent (mock)",
                to=to_email,
                subject=subject,
            )
            return True

        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return False

    @staticmethod
    def build_deadline_reminder_email(
        rfp: RFP,
        days_until: int,
    ) -> tuple[str, str, str]:
        """
        Build deadline reminder email content.

        Returns: (subject, html_body, text_body)
        """
        subject = (
            f"⏰ RFP Deadline in {days_until} day{'s' if days_until != 1 else ''}: {rfp.title[:50]}"
        )

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #1a365d; color: white; padding: 20px; text-align: center;">
                <h1 style="margin: 0;">RFP Sniper</h1>
            </div>

            <div style="padding: 20px;">
                <h2>⏰ Deadline Reminder</h2>

                <p>The response deadline for the following opportunity is in <strong>{days_until} day{'s' if days_until != 1 else ''}</strong>:</p>

                <div style="background: #f7f7f7; padding: 15px; border-left: 4px solid #e53e3e; margin: 20px 0;">
                    <h3 style="margin-top: 0;">{rfp.title}</h3>
                    <p><strong>Solicitation:</strong> {rfp.solicitation_number}</p>
                    <p><strong>Agency:</strong> {rfp.agency}</p>
                    <p><strong>Deadline:</strong> {rfp.response_deadline.strftime('%B %d, %Y at %I:%M %p') if rfp.response_deadline else 'TBD'}</p>
                </div>

                <p>
                    <a href="{settings.app_url}/opportunities/{rfp.id}"
                       style="background: #3182ce; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        View in RFP Sniper
                    </a>
                </p>
            </div>

            <div style="background: #f7f7f7; padding: 15px; text-align: center; font-size: 12px; color: #666;">
                <p>You're receiving this because you have deadline reminders enabled.</p>
                <p><a href="{settings.app_url}/settings/notifications">Manage notification preferences</a></p>
            </div>
        </body>
        </html>
        """

        text_body = f"""
RFP Sniper - Deadline Reminder

The response deadline for the following opportunity is in {days_until} day{'s' if days_until != 1 else ''}:

{rfp.title}
Solicitation: {rfp.solicitation_number}
Agency: {rfp.agency}
Deadline: {rfp.response_deadline.strftime('%B %d, %Y at %I:%M %p') if rfp.response_deadline else 'TBD'}

View in RFP Sniper: {settings.app_url}/opportunities/{rfp.id}
        """

        return subject, html_body, text_body


email_service = EmailService()


# =============================================================================
# Slack Service
# =============================================================================


class SlackService:
    """
    Slack webhook notification service.
    """

    @staticmethod
    async def send_webhook(
        webhook_url: str,
        message: dict,
    ) -> bool:
        """
        Send a message to Slack via webhook.
        """
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json=message,
                    timeout=10.0,
                )
                return response.status_code == 200

        except Exception as e:
            logger.error(f"Slack webhook failed: {e}")
            return False

    @staticmethod
    def build_deadline_message(rfp: RFP, days_until: int) -> dict:
        """Build Slack message for deadline reminder."""
        return {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"⏰ RFP Deadline in {days_until} Day{'s' if days_until != 1 else ''}",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Title:*\n{rfp.title[:100]}"},
                        {"type": "mrkdwn", "text": f"*Agency:*\n{rfp.agency}"},
                        {"type": "mrkdwn", "text": f"*Solicitation:*\n{rfp.solicitation_number}"},
                        {
                            "type": "mrkdwn",
                            "text": f"*Deadline:*\n{rfp.response_deadline.strftime('%B %d, %Y') if rfp.response_deadline else 'TBD'}",
                        },
                    ],
                },
            ],
        }


slack_service = SlackService()


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/", response_model=list[NotificationResponse])
async def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[NotificationResponse]:
    """
    List user's notifications.
    """
    query = select(Notification).where(Notification.user_id == current_user.id)

    if unread_only:
        query = query.where(Notification.is_read == False)

    query = query.order_by(Notification.created_at.desc()).limit(limit)

    result = await session.execute(query)
    notifications = list(result.scalars().all())

    return [
        NotificationResponse(
            id=n.id,
            notification_type=n.notification_type.value,
            title=n.title,
            message=n.message,
            is_read=n.is_read,
            rfp_id=n.rfp_id,
            proposal_id=n.proposal_id,
            created_at=n.created_at,
        )
        for n in notifications
    ]


@router.get("/unread-count")
async def get_unread_count(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Get count of unread notifications.
    """
    from sqlalchemy import func

    result = await session.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == current_user.id,
            Notification.is_read == False,
        )
    )
    count = result.scalar()

    return {"unread_count": count or 0}


@router.post("/{notification_id}/read")
async def mark_as_read(
    notification_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Mark a notification as read.
    """
    result = await session.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.is_read = True
    await session.commit()

    return {"message": "Notification marked as read"}


@router.post("/read-all")
async def mark_all_as_read(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Mark all notifications as read.
    """
    from sqlalchemy import update

    await session.execute(
        update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.is_read == False,
        )
        .values(is_read=True)
    )
    await session.commit()

    return {"message": "All notifications marked as read"}


# =============================================================================
# Preferences
# =============================================================================


@router.get("/preferences")
async def get_preferences(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Get user's notification preferences.
    """
    result = await session.execute(
        select(NotificationPreferences).where(NotificationPreferences.user_id == current_user.id)
    )
    prefs = result.scalar_one_or_none()

    if not prefs:
        # Create default preferences
        prefs = NotificationPreferences(user_id=current_user.id)
        session.add(prefs)
        await session.commit()
        await session.refresh(prefs)

    return {
        "email_enabled": prefs.email_enabled,
        "email_address": prefs.email_address,
        "deadline_reminders": prefs.deadline_reminders,
        "deadline_days_before": prefs.deadline_days_before,
        "rfp_matches": prefs.rfp_matches,
        "analysis_complete": prefs.analysis_complete,
        "generation_complete": prefs.generation_complete,
        "team_activity": prefs.team_activity,
        "slack_enabled": prefs.slack_enabled,
        "slack_webhook_url": prefs.slack_webhook_url,
        "quiet_hours_enabled": prefs.quiet_hours_enabled,
        "quiet_hours_start": prefs.quiet_hours_start,
        "quiet_hours_end": prefs.quiet_hours_end,
    }


@router.put("/preferences")
async def update_preferences(
    request: PreferencesUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Update notification preferences.
    """
    result = await session.execute(
        select(NotificationPreferences).where(NotificationPreferences.user_id == current_user.id)
    )
    prefs = result.scalar_one_or_none()

    if not prefs:
        prefs = NotificationPreferences(user_id=current_user.id)
        session.add(prefs)

    # Update fields
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(prefs, field, value)

    prefs.updated_at = datetime.utcnow()
    await session.commit()

    logger.info("Notification preferences updated", user_id=current_user.id)

    return {"message": "Preferences updated successfully"}


# =============================================================================
# Notification Creation Helpers
# =============================================================================


async def create_notification(
    session: AsyncSession,
    user_id: int,
    notification_type: NotificationType,
    title: str,
    message: str,
    rfp_id: int = None,
    proposal_id: int = None,
    metadata: dict = None,
) -> Notification:
    """
    Create a notification for a user.
    """
    notification = Notification(
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        message=message,
        rfp_id=rfp_id,
        proposal_id=proposal_id,
        meta=metadata or {},
    )

    session.add(notification)
    await session.commit()
    await session.refresh(notification)

    return notification


async def send_deadline_reminders(session: AsyncSession):
    """
    Check for upcoming deadlines and send reminders.
    Called by Celery beat scheduler.
    """
    # Get all users with preferences
    users_result = await session.execute(
        select(User, NotificationPreferences)
        .join(
            NotificationPreferences,
            User.id == NotificationPreferences.user_id,
        )
        .where(NotificationPreferences.deadline_reminders == True)
    )

    for user, prefs in users_result.all():
        reminder_days = prefs.deadline_days_before or [7, 3, 1]

        for days in reminder_days:
            target_date = datetime.utcnow().date() + timedelta(days=days)

            # Find RFPs with deadline on target date
            rfps_result = await session.execute(
                select(RFP)
                .where(
                    RFP.user_id == user.id,
                    RFP.response_deadline != None,
                )
                .where(
                    RFP.response_deadline >= datetime.combine(target_date, datetime.min.time()),
                    RFP.response_deadline
                    < datetime.combine(target_date + timedelta(days=1), datetime.min.time()),
                )
            )

            for rfp in rfps_result.scalars().all():
                # Create in-app notification
                await create_notification(
                    session=session,
                    user_id=user.id,
                    notification_type=NotificationType.DEADLINE_REMINDER,
                    title=f"RFP Deadline in {days} day{'s' if days != 1 else ''}",
                    message=f"{rfp.title} - {rfp.agency}",
                    rfp_id=rfp.id,
                )

                # Send email if enabled
                if prefs.email_enabled and prefs.email_address:
                    subject, html, text = email_service.build_deadline_reminder_email(rfp, days)
                    await email_service.send_email(prefs.email_address, subject, html, text)

                # Send Slack if enabled
                if prefs.slack_enabled and prefs.slack_webhook_url:
                    message = slack_service.build_deadline_message(rfp, days)
                    await slack_service.send_webhook(prefs.slack_webhook_url, message)

    logger.info("Deadline reminders sent")
