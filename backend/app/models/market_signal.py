"""Market signals and subscriptions models."""

from datetime import datetime
from enum import Enum

from pydantic import field_validator
from sqlmodel import JSON, Column, Field, SQLModel, Text


class SignalType(str, Enum):
    BUDGET = "budget"
    AWARD = "award"
    NEWS = "news"
    CONGRESSIONAL = "congressional"
    RECOMPETE = "recompete"


class DigestFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"


class MarketSignal(SQLModel, table=True):
    __tablename__ = "market_signals"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int | None = Field(default=None, foreign_key="users.id", index=True)
    title: str = Field(max_length=255)
    signal_type: SignalType = Field(default=SignalType.NEWS)
    agency: str | None = Field(default=None, max_length=255, index=True)
    content: str | None = Field(default=None, sa_column=Column(Text))
    source_url: str | None = Field(default=None, max_length=500)
    relevance_score: float = Field(default=0.0)
    published_at: datetime | None = None
    is_read: bool = Field(default=False)

    @field_validator("published_at", mode="after")
    @classmethod
    def strip_timezone(cls, v: datetime | None) -> datetime | None:
        """DB uses TIMESTAMP WITHOUT TIME ZONE — normalize to naive UTC."""
        if v is not None and v.tzinfo is not None:
            return v.replace(tzinfo=None)
        return v

    created_at: datetime = Field(default_factory=datetime.utcnow)


class SignalSubscription(SQLModel, table=True):
    __tablename__ = "signal_subscriptions"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    agencies: list = Field(default=[], sa_column=Column(JSON))
    naics_codes: list = Field(default=[], sa_column=Column(JSON))
    keywords: list = Field(default=[], sa_column=Column(JSON))
    email_digest_enabled: bool = Field(default=False)
    digest_frequency: DigestFrequency = Field(default=DigestFrequency.DAILY)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
