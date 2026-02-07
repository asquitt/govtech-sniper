"""
RFP Sniper - Integration Models
===============================
Stores integration configuration (SSO, CRM, storage, etc.).
"""

from datetime import datetime
from typing import Optional
from enum import Enum

from sqlmodel import Field, SQLModel, Column, JSON


class IntegrationProvider(str, Enum):
    OKTA = "okta"
    MICROSOFT = "microsoft"
    SHAREPOINT = "sharepoint"
    SALESFORCE = "salesforce"
    WORD_ADDIN = "word_addin"
    WEBHOOK = "webhook"
    SLACK = "slack"
    UNANET = "unanet"


class IntegrationSyncStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class IntegrationConfig(SQLModel, table=True):
    """
    Integration configuration record.
    """
    __tablename__ = "integrations"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)

    provider: IntegrationProvider = Field(index=True)
    name: Optional[str] = Field(default=None, max_length=255)
    is_enabled: bool = Field(default=True)

    # Encrypted config stored as JSON (client secrets, endpoints, etc.)
    config: dict = Field(default={}, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class IntegrationSyncRun(SQLModel, table=True):
    """
    Integration sync history for external systems.
    """
    __tablename__ = "integration_sync_runs"

    id: Optional[int] = Field(default=None, primary_key=True)
    integration_id: int = Field(foreign_key="integrations.id", index=True)
    provider: IntegrationProvider = Field(index=True)

    status: IntegrationSyncStatus = Field(default=IntegrationSyncStatus.PENDING)
    items_synced: int = Field(default=0)
    error: Optional[str] = Field(default=None, max_length=1000)
    details: dict = Field(default={}, sa_column=Column(JSON))

    started_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    completed_at: Optional[datetime] = None


class IntegrationWebhookEvent(SQLModel, table=True):
    """
    Inbound webhook event payloads for integrations.
    """
    __tablename__ = "integration_webhook_events"

    id: Optional[int] = Field(default=None, primary_key=True)
    integration_id: int = Field(foreign_key="integrations.id", index=True)
    provider: IntegrationProvider = Field(index=True)

    event_type: str = Field(default="generic", max_length=128, index=True)
    payload: dict = Field(default={}, sa_column=Column(JSON))

    received_at: datetime = Field(default_factory=datetime.utcnow, index=True)
