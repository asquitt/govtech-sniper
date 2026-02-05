"""
RFP Sniper - Audit Event Models
===============================
Security and compliance audit trail.
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel, Column, JSON


class AuditEvent(SQLModel, table=True):
    """
    Audit log entry for sensitive or business-critical actions.
    """
    __tablename__ = "audit_events"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Actor
    user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)

    # Target entity
    entity_type: str = Field(max_length=64, index=True)
    entity_id: Optional[int] = Field(default=None, index=True)

    # Action descriptor, e.g., rfp.created, document.uploaded
    action: str = Field(max_length=128, index=True)

    # Optional metadata for context (immutable snapshot)
    metadata: dict = Field(default={}, sa_column=Column(JSON))

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
