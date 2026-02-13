"""Market signal and subscription schemas."""

from datetime import datetime

from pydantic import BaseModel, field_validator

from app.models.market_signal import DigestFrequency, SignalType


class SignalCreate(BaseModel):
    title: str
    signal_type: SignalType = SignalType.NEWS
    agency: str | None = None
    content: str | None = None
    source_url: str | None = None
    relevance_score: float = 0.0
    published_at: datetime | None = None

    @field_validator("published_at", mode="after")
    @classmethod
    def strip_timezone(cls, v: datetime | None) -> datetime | None:
        """DB uses TIMESTAMP WITHOUT TIME ZONE — normalize to naive UTC."""
        if v is not None and v.tzinfo is not None:
            return v.replace(tzinfo=None)
        return v


class SignalRead(BaseModel):
    id: int
    user_id: int | None
    title: str
    signal_type: SignalType
    agency: str | None
    content: str | None
    source_url: str | None
    relevance_score: float
    published_at: datetime | None
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SignalListResponse(BaseModel):
    signals: list[SignalRead]
    total: int


class SubscriptionCreate(BaseModel):
    agencies: list[str] = []
    naics_codes: list[str] = []
    keywords: list[str] = []
    email_digest_enabled: bool = False
    digest_frequency: DigestFrequency = DigestFrequency.DAILY


class SubscriptionRead(BaseModel):
    id: int
    user_id: int
    agencies: list[str]
    naics_codes: list[str]
    keywords: list[str]
    email_digest_enabled: bool
    digest_frequency: DigestFrequency
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
