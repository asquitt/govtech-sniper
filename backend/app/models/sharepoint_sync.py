"""
RFP Sniper - SharePoint Sync Models
====================================
Configuration and logging for SharePoint auto-sync and folder watching.
"""

from datetime import datetime
from enum import Enum

from sqlmodel import JSON, Column, Field, SQLModel


class SyncDirection(str, Enum):
    PUSH = "push"
    PULL = "pull"
    BIDIRECTIONAL = "bidirectional"


class SharePointSyncConfig(SQLModel, table=True):
    """User-configured SharePoint sync schedule for a proposal."""

    __tablename__ = "sharepoint_sync_configs"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    proposal_id: int = Field(foreign_key="proposals.id", index=True)

    sharepoint_folder: str = Field(max_length=512)
    sync_direction: SyncDirection = Field(default=SyncDirection.PUSH)
    auto_sync_enabled: bool = Field(default=False)
    watch_for_rfps: bool = Field(default=False)

    last_synced_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SharePointSyncLog(SQLModel, table=True):
    """Audit log for SharePoint sync operations."""

    __tablename__ = "sharepoint_sync_logs"

    id: int | None = Field(default=None, primary_key=True)
    config_id: int = Field(foreign_key="sharepoint_sync_configs.id", index=True)

    action: str = Field(max_length=64)  # push, pull, watch_detect
    status: str = Field(max_length=32, index=True)  # success, failed
    details: dict = Field(default={}, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
