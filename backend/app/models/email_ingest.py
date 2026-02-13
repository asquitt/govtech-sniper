"""Email ingestion configuration and history models."""

from datetime import datetime
from enum import Enum

from sqlmodel import Column, Field, SQLModel, Text


class EmailProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    IGNORED = "ignored"
    ERROR = "error"


class EmailIngestConfig(SQLModel, table=True):
    __tablename__ = "email_ingest_configs"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    imap_server: str = Field(max_length=255)
    imap_port: int = Field(default=993)
    email_address: str = Field(max_length=255)
    encrypted_password: str = Field(max_length=500)
    folder: str = Field(default="INBOX", max_length=255)
    is_enabled: bool = Field(default=True)
    last_checked_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class IngestedEmail(SQLModel, table=True):
    __tablename__ = "ingested_emails"

    id: int | None = Field(default=None, primary_key=True)
    config_id: int = Field(foreign_key="email_ingest_configs.id", index=True)
    message_id: str = Field(max_length=500, unique=True)
    subject: str = Field(max_length=500)
    sender: str = Field(max_length=255)
    received_at: datetime = Field(default_factory=datetime.utcnow)
    body_text: str | None = Field(default=None, sa_column=Column(Text))
    processing_status: EmailProcessingStatus = Field(
        default=EmailProcessingStatus.PENDING, index=True
    )
    created_rfp_id: int | None = Field(default=None, foreign_key="rfps.id", nullable=True)
    error_message: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=datetime.utcnow)
