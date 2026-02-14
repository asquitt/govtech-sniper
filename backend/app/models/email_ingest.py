"""Email ingestion configuration and history models."""

from datetime import datetime
from enum import Enum

from sqlalchemy import UniqueConstraint
from sqlmodel import JSON, Column, Field, SQLModel, Text


class EmailProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    IGNORED = "ignored"
    ERROR = "error"


class EmailIngestConfig(SQLModel, table=True):
    __tablename__ = "email_ingest_configs"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    workspace_id: int | None = Field(
        default=None,
        foreign_key="shared_workspaces.id",
        index=True,
    )
    imap_server: str = Field(max_length=255)
    imap_port: int = Field(default=993)
    email_address: str = Field(max_length=255)
    encrypted_password: str = Field(max_length=500)
    folder: str = Field(default="INBOX", max_length=255)
    is_enabled: bool = Field(default=True)
    auto_create_rfps: bool = Field(default=True)
    min_rfp_confidence: float = Field(default=0.35, ge=0.0, le=1.0)
    last_checked_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class IngestedEmail(SQLModel, table=True):
    __tablename__ = "ingested_emails"
    __table_args__ = (
        UniqueConstraint(
            "config_id",
            "message_id",
            name="uq_ingested_emails_config_message_id",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    config_id: int = Field(foreign_key="email_ingest_configs.id", index=True)
    message_id: str = Field(max_length=500)
    subject: str = Field(max_length=500)
    sender: str = Field(max_length=255)
    received_at: datetime = Field(default_factory=datetime.utcnow)
    body_text: str | None = Field(default=None, sa_column=Column(Text))
    attachment_count: int = Field(default=0, ge=0)
    attachment_names: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    processing_status: EmailProcessingStatus = Field(
        default=EmailProcessingStatus.PENDING, index=True
    )
    classification_confidence: float | None = None
    classification_reasons: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    created_rfp_id: int | None = Field(default=None, foreign_key="rfps.id", nullable=True)
    error_message: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: datetime | None = None
