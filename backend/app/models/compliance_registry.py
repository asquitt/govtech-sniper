"""
Compliance Control-Evidence Registry.

Maps security controls (NIST 800-171, CMMC, FedRAMP) to evidence artifacts
for audit-ready compliance tracking.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlmodel import Column, Field, SQLModel, Text


class ControlFramework(str, Enum):
    NIST_800_171 = "nist_800_171"
    CMMC_L2 = "cmmc_l2"
    FEDRAMP = "fedramp"
    FAR_52_204_21 = "far_52_204_21"
    SOC2 = "soc2"


class ControlStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    IMPLEMENTED = "implemented"
    ASSESSED = "assessed"
    NOT_APPLICABLE = "not_applicable"


class EvidenceType(str, Enum):
    POLICY = "policy"
    PROCEDURE = "procedure"
    SCREENSHOT = "screenshot"
    LOG = "log"
    CONFIGURATION = "configuration"
    ATTESTATION = "attestation"
    SCAN_REPORT = "scan_report"


class ComplianceControl(SQLModel, table=True):
    """A security control from a compliance framework."""

    __tablename__ = "compliance_controls"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)

    framework: ControlFramework
    control_id: str = Field(max_length=50)  # e.g. "AC-1", "3.1.1"
    title: str = Field(max_length=255)
    description: str | None = Field(default=None, sa_column=Column(Text))

    status: ControlStatus = Field(default=ControlStatus.NOT_STARTED)
    implementation_notes: str | None = Field(default=None, sa_column=Column(Text))
    assessor_notes: str | None = Field(default=None, sa_column=Column(Text))

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ComplianceEvidence(SQLModel, table=True):
    """An evidence artifact linked to one or more controls."""

    __tablename__ = "compliance_evidence"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)

    title: str = Field(max_length=255)
    evidence_type: EvidenceType
    description: str | None = Field(default=None, sa_column=Column(Text))
    file_path: str | None = Field(default=None, max_length=500)
    url: str | None = Field(default=None, max_length=500)

    collected_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ControlEvidenceLink(SQLModel, table=True):
    """Links evidence artifacts to controls (many-to-many)."""

    __tablename__ = "control_evidence_links"

    id: int | None = Field(default=None, primary_key=True)
    control_id: int = Field(foreign_key="compliance_controls.id", index=True)
    evidence_id: int = Field(foreign_key="compliance_evidence.id", index=True)

    linked_by_user_id: int = Field(foreign_key="users.id")
    notes: str | None = Field(default=None, max_length=500)

    created_at: datetime = Field(default_factory=datetime.utcnow)
