"""
RFP Sniper - Collaboration Schemas
====================================
Request/response models for workspaces, invitations, and data sharing.
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel


class WorkspaceCreate(BaseModel):
    name: str
    rfp_id: Optional[int] = None
    description: Optional[str] = None


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class WorkspaceRead(BaseModel):
    id: int
    owner_id: int
    rfp_id: Optional[int] = None
    name: str
    description: Optional[str] = None
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
    user_email: Optional[str] = None
    user_name: Optional[str] = None
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
    workspace_description: Optional[str] = None
    rfp_title: Optional[str] = None
    shared_items: List[SharedDataRead] = []
    members: List[MemberRead] = []
