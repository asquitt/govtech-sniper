"""
RFP Sniper - Collaboration Schemas
====================================
Request/response models for workspaces, invitations, and data sharing.
"""

from datetime import datetime

from pydantic import BaseModel


class WorkspaceCreate(BaseModel):
    name: str
    rfp_id: int | None = None
    description: str | None = None


class WorkspaceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class WorkspaceRead(BaseModel):
    id: int
    owner_id: int
    rfp_id: int | None = None
    name: str
    description: str | None = None
    member_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InvitationCreate(BaseModel):
    email: str
    role: str = "viewer"


class InvitationRead(BaseModel):
    id: int
    workspace_id: int
    email: str
    role: str
    is_accepted: bool
    expires_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class MemberRead(BaseModel):
    id: int
    workspace_id: int
    user_id: int
    role: str
    user_email: str | None = None
    user_name: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ShareDataCreate(BaseModel):
    data_type: str  # rfp_summary, compliance_matrix, proposal_section, forecast, contract_feed
    entity_id: int


class SharedDataRead(BaseModel):
    id: int
    workspace_id: int
    data_type: str
    entity_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class PortalView(BaseModel):
    """Read-only partner portal view of a workspace."""

    workspace_name: str
    workspace_description: str | None = None
    rfp_title: str | None = None
    shared_items: list[SharedDataRead] = []
    members: list[MemberRead] = []
