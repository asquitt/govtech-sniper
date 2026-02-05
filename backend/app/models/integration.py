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
