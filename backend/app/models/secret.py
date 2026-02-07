"""
RFP Sniper - Secret Vault Model
===============================
Encrypted secret storage for integrations and operational keys.
"""

from datetime import datetime

from sqlmodel import Field, SQLModel


class SecretRecord(SQLModel, table=True):
    __tablename__ = "secret_records"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    key: str = Field(max_length=255, index=True)
    value_encrypted: str = Field(max_length=2000)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
