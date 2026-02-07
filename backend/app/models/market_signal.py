"""Market signals and subscriptions models."""

from datetime import datetime
from typing import Optional
from enum import Enum

from sqlmodel import Field, SQLModel, Column, Text, JSON


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

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)
    title: str = Field(max_length=255)
    signal_type: SignalType = Field(default=SignalType.NEWS)
    agency: Optional[str] = Field(default=None, max_length=255, index=True)
    content: Optional[str] = Field(default=None, sa_column=Column(Text))
    source_url: Optional[str] = Field(default=None, max_length=500)
    relevance_score: float = Field(default=0.0)
    published_at: Optional[datetime] = None
    is_read: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SignalSubscription(SQLModel, table=True):
    __tablename__ = "signal_subscriptions"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    agencies: list = Field(default=[], sa_column=Column(JSON))
    naics_codes: list = Field(default=[], sa_column=Column(JSON))
    keywords: list = Field(default=[], sa_column=Column(JSON))
    email_digest_enabled: bool = Field(default=False)
    digest_frequency: DigestFrequency = Field(default=DigestFrequency.DAILY)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
