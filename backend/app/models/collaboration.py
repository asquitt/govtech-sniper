"""
RFP Sniper - Collaboration Models
===================================
Cross-organization collaboration: shared workspaces, invitations, and data permissions.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, String, Text
from sqlmodel import Field, SQLModel


class WorkspaceRole(str, Enum):
    VIEWER = "viewer"
    CONTRIBUTOR = "contributor"
    ADMIN = "admin"


class SharedDataType(str, Enum):
    RFP_SUMMARY = "rfp_summary"
    COMPLIANCE_MATRIX = "compliance_matrix"
    PROPOSAL_SECTION = "proposal_section"
    FORECAST = "forecast"
    CONTRACT_FEED = "contract_feed"


class SharedWorkspace(SQLModel, table=True):
    """A collaboration workspace owned by a user, optionally tied to an RFP."""
    __tablename__ = "shared_workspaces"

    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="users.id", index=True)
    rfp_id: Optional[int] = Field(default=None, foreign_key="rfps.id", index=True)
    name: str = Field(max_length=255)
    description: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class WorkspaceInvitation(SQLModel, table=True):
    """Email-based invitation to join a workspace."""
    __tablename__ = "workspace_invitations"

    id: Optional[int] = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="shared_workspaces.id", index=True)
    email: str = Field(max_length=255, index=True)
    role: WorkspaceRole = Field(default=WorkspaceRole.VIEWER)
    token: str = Field(max_length=255, sa_column=Column(String(255), unique=True))
    expires_at: datetime
    is_accepted: bool = Field(default=False)
    accepted_user_id: Optional[int] = Field(
        default=None, foreign_key="users.id"
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)


class WorkspaceMember(SQLModel, table=True):
    """Active member of a workspace (created after invitation acceptance)."""
    __tablename__ = "workspace_members"

    id: Optional[int] = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="shared_workspaces.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    role: WorkspaceRole = Field(default=WorkspaceRole.VIEWER)

    created_at: datetime = Field(default_factory=datetime.utcnow)


class SharedDataPermission(SQLModel, table=True):
    """Controls which data items are visible inside a workspace."""
    __tablename__ = "shared_data_permissions"

    id: Optional[int] = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="shared_workspaces.id", index=True)
    data_type: SharedDataType
    entity_id: int  # ID of the shared entity (rfp_id, proposal_id, etc.)

    created_at: datetime = Field(default_factory=datetime.utcnow)
