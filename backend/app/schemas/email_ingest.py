"""Email ingest configuration and history schemas."""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel

from app.models.email_ingest import ProcessingStatus


class EmailIngestConfigCreate(BaseModel):
    imap_server: str
    imap_port: int = 993
    email_address: str
    password: str
    folder: str = "INBOX"


class EmailIngestConfigUpdate(BaseModel):
    imap_server: Optional[str] = None
    imap_port: Optional[int] = None
    email_address: Optional[str] = None
    password: Optional[str] = None
    folder: Optional[str] = None
    is_enabled: Optional[bool] = None


class EmailIngestConfigRead(BaseModel):
    id: int
    user_id: int
    imap_server: str
    imap_port: int
    email_address: str
    encrypted_password: str
    folder: str
    is_enabled: bool
    last_checked_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    def mask_password(self) -> "EmailIngestConfigRead":
        """Return a copy with the password masked."""
        return self.model_copy(update={"encrypted_password": "********"})


class IngestedEmailRead(BaseModel):
    id: int
    config_id: int
    message_id: str
    subject: str
    sender: str
    received_at: datetime
    processing_status: ProcessingStatus
    created_rfp_id: Optional[int]
    error_message: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class EmailIngestListResponse(BaseModel):
    items: List[IngestedEmailRead]
    total: int
