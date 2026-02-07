"""Market signal and subscription schemas."""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel

from app.models.market_signal import SignalType, DigestFrequency


class SignalCreate(BaseModel):
    title: str
    signal_type: SignalType = SignalType.NEWS
    agency: Optional[str] = None
    content: Optional[str] = None
    source_url: Optional[str] = None
    relevance_score: float = 0.0
    published_at: Optional[datetime] = None


class SignalRead(BaseModel):
    id: int
    user_id: Optional[int]
    title: str
    signal_type: SignalType
    agency: Optional[str]
    content: Optional[str]
    source_url: Optional[str]
    relevance_score: float
    published_at: Optional[datetime]
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SignalListResponse(BaseModel):
    signals: List[SignalRead]
    total: int


class SubscriptionCreate(BaseModel):
    agencies: List[str] = []
    naics_codes: List[str] = []
    keywords: List[str] = []
    email_digest_enabled: bool = False
    digest_frequency: DigestFrequency = DigestFrequency.DAILY


class SubscriptionRead(BaseModel):
    id: int
    user_id: int
    agencies: List[str]
    naics_codes: List[str]
    keywords: List[str]
    email_digest_enabled: bool
    digest_frequency: DigestFrequency
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
