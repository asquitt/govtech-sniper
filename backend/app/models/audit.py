"""
RFP Sniper - Audit Event Models
===============================
Security and compliance audit trail.
"""

from datetime import datetime

from sqlmodel import JSON, Column, Field, SQLModel


class AuditEvent(SQLModel, table=True):
    """
    Audit log entry for sensitive or business-critical actions.
    """

    __tablename__ = "audit_events"

    id: int | None = Field(default=None, primary_key=True)

    # Actor
    user_id: int | None = Field(default=None, foreign_key="users.id", index=True)

    # Target entity
    entity_type: str = Field(max_length=64, index=True)
    entity_id: int | None = Field(default=None, index=True)

    # Action descriptor, e.g., rfp.created, document.uploaded
    action: str = Field(max_length=128, index=True)

    # Optional metadata for context (immutable snapshot)
    event_metadata: dict = Field(default={}, sa_column=Column("metadata", JSON))

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
