"""Email ingest configuration and history schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.email_ingest import EmailProcessingStatus


class EmailIngestConfigCreate(BaseModel):
    imap_server: str
    imap_port: int = 993
    email_address: str
    password: str
    folder: str = "INBOX"
    workspace_id: int | None = None
    auto_create_rfps: bool = True
    min_rfp_confidence: float = Field(default=0.35, ge=0.0, le=1.0)


class EmailIngestConfigUpdate(BaseModel):
    imap_server: str | None = None
    imap_port: int | None = None
    email_address: str | None = None
    password: str | None = None
    folder: str | None = None
    is_enabled: bool | None = None
    workspace_id: int | None = None
    auto_create_rfps: bool | None = None
    min_rfp_confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class EmailIngestConfigRead(BaseModel):
    id: int
    user_id: int
    workspace_id: int | None
    imap_server: str
    imap_port: int
    email_address: str
    encrypted_password: str
    folder: str
    is_enabled: bool
    auto_create_rfps: bool
    min_rfp_confidence: float
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
    attachment_count: int
    attachment_names: list[str]
    processing_status: EmailProcessingStatus
    classification_confidence: float | None
    classification_reasons: list[str]
    created_rfp_id: int | None
    error_message: str | None
    created_at: datetime
    processed_at: datetime | None

    model_config = {"from_attributes": True}


class EmailIngestListResponse(BaseModel):
    items: list[IngestedEmailRead]
    total: int


class EmailIngestSyncRequest(BaseModel):
    config_id: int | None = None
    run_poll: bool = True
    run_process: bool = True
    poll_limit: int = Field(default=50, ge=1, le=200)
    process_limit: int = Field(default=100, ge=1, le=500)


class EmailIngestSyncResponse(BaseModel):
    configs_checked: int
    fetched: int
    duplicates: int
    poll_errors: int
    processed: int
    created_rfps: int
    inbox_forwarded: int
    process_errors: int
