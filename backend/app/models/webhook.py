"""
RFP Sniper - Webhook Models
===========================
Webhook subscriptions and delivery logs.
"""

from datetime import datetime
from enum import Enum

from sqlmodel import JSON, Column, Field, SQLModel


class WebhookDeliveryStatus(str, Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    SKIPPED = "skipped"


class WebhookSubscription(SQLModel, table=True):
    """
    Webhook subscription configuration.
    """

    __tablename__ = "webhook_subscriptions"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)

    name: str = Field(max_length=255)
    target_url: str = Field(max_length=1000)
    secret: str | None = Field(default=None, max_length=255)

    event_types: list[str] = Field(default=[], sa_column=Column(JSON))
    is_active: bool = Field(default=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class WebhookDelivery(SQLModel, table=True):
    """
    Delivery log for webhook events.
    """

    __tablename__ = "webhook_deliveries"

    id: int | None = Field(default=None, primary_key=True)
    subscription_id: int = Field(foreign_key="webhook_subscriptions.id", index=True)

    event_type: str = Field(max_length=128, index=True)
    payload: dict = Field(default={}, sa_column=Column(JSON))

    status: WebhookDeliveryStatus = Field(default=WebhookDeliveryStatus.PENDING)
    response_code: int | None = None
    response_body: str | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    delivered_at: datetime | None = None
