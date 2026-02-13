"""Email ingest configuration and history schemas."""

from datetime import datetime

from pydantic import BaseModel

from app.models.email_ingest import EmailProcessingStatus


class EmailIngestConfigCreate(BaseModel):
    imap_server: str
    imap_port: int = 993
    email_address: str
    password: str
    folder: str = "INBOX"


class EmailIngestConfigUpdate(BaseModel):
    imap_server: str | None = None
    imap_port: int | None = None
    email_address: str | None = None
    password: str | None = None
    folder: str | None = None
    is_enabled: bool | None = None


class EmailIngestConfigRead(BaseModel):
    id: int
    user_id: int
    imap_server: str
    imap_port: int
    email_address: str
    encrypted_password: str
    folder: str
    is_enabled: bool
    last_checked_at: datetime | None
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
    processing_status: EmailProcessingStatus
    created_rfp_id: int | None
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class EmailIngestListResponse(BaseModel):
    items: list[IngestedEmailRead]
    total: int
