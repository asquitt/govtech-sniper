"""
RFP Sniper - SCIM Provisioning Routes
====================================
Minimal SCIM 2.0 endpoints for user provisioning and group role mapping.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Dict, Any
import json
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.config import settings
from app.database import get_session
from app.models.user import User, UserTier
from app.api.routes.teams import Team, TeamMember, TeamRole
from app.services.auth_service import hash_password
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/scim/v2", tags=["SCIM"])


# =============================================================================
# Auth Dependency
# =============================================================================

def require_scim_token(authorization: Optional[str] = Header(default=None)) -> None:
    expected = settings.scim_bearer_token
    if not expected:
        raise HTTPException(status_code=503, detail="SCIM not configured")
    if authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Invalid SCIM token")


# =============================================================================
# SCIM Schemas (Minimal)
# =============================================================================

class ScimEmail(BaseModel):
    value: EmailStr
    primary: Optional[bool] = None


class ScimName(BaseModel):
    givenName: Optional[str] = None
    familyName: Optional[str] = None


class ScimUserCreate(BaseModel):
    userName: EmailStr
    active: Optional[bool] = True
    name: Optional[ScimName] = None
    emails: Optional[List[ScimEmail]] = None
    externalId: Optional[str] = None
    groups: Optional[List[Dict[str, Any]]] = None


class ScimUserPatch(BaseModel):
    active: Optional[bool] = None


class ScimGroupCreate(BaseModel):
    displayName: str
    members: Optional[List[Dict[str, Any]]] = None


class ScimListResponse(BaseModel):
    schemas: List[str]
    totalResults: int
    startIndex: int
    itemsPerPage: int
    Resources: List[Dict[str, Any]]


# =============================================================================
# Helpers
# =============================================================================

def _parse_group_role_map() -> Dict[str, str]:
    if not settings.scim_group_role_map:
        return {}
    try:
        return json.loads(settings.scim_group_role_map)
    except json.JSONDecodeError:
        return {}


def _resolve_role(groups: Optional[List[Dict[str, Any]]]) -> TeamRole:
    mapping = _parse_group_role_map()
    try:
        default_role = TeamRole(settings.scim_default_role)
    except ValueError:
        default_role = TeamRole.MEMBER
    if not groups:
        return default_role

    role_priority = [TeamRole.OWNER, TeamRole.ADMIN, TeamRole.MEMBER, TeamRole.VIEWER]
    resolved: Optional[TeamRole] = None
    for group in groups:
        name = group.get("display") or group.get("value")
        if not name or name not in mapping:
            continue
        try:
            mapped = TeamRole(mapping[name])
        except ValueError:
            continue
        if resolved is None or role_priority.index(mapped) < role_priority.index(resolved):
            resolved = mapped
    return resolved or default_role


async def _get_or_create_default_team(
    session: AsyncSession,
    owner_id: int,
) -> Team:
    result = await session.execute(
        select(Team).where(Team.name == settings.scim_default_team_name)
    )
    team = result.scalar_one_or_none()
    if team:
        return team

    if not settings.scim_auto_create_team:
        raise HTTPException(status_code=400, detail="Default team not configured")

    team = Team(
        name=settings.scim_default_team_name,
        description="Provisioned via SCIM",
        owner_id=owner_id,
        settings={},
    )
    session.add(team)
    await session.flush()
    return team


def _scim_user_resource(user: User) -> Dict[str, Any]:
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "id": str(user.id),
        "userName": user.email,
        "active": user.is_active,
        "name": {
            "givenName": user.full_name.split(" ")[0] if user.full_name else None,
            "familyName": " ".join(user.full_name.split(" ")[1:]) if user.full_name else None,
        },
        "emails": [{"value": user.email, "primary": True}],
        "meta": {"resourceType": "User", "created": user.created_at.isoformat()},
    }


def _scim_group_resource(team: Team) -> Dict[str, Any]:
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
        "id": str(team.id),
        "displayName": team.name,
        "meta": {"resourceType": "Group", "created": team.created_at.isoformat()},
    }


# =============================================================================
# SCIM Endpoints
# =============================================================================

@router.get("/Users", response_model=ScimListResponse, dependencies=[Depends(require_scim_token)])
async def list_scim_users(
    session: AsyncSession = Depends(get_session),
) -> ScimListResponse:
    result = await session.execute(select(User))
    users = result.scalars().all()
    resources = [_scim_user_resource(user) for user in users]
    return ScimListResponse(
        schemas=["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        totalResults=len(resources),
        startIndex=1,
        itemsPerPage=len(resources),
        Resources=resources,
    )


@router.post("/Users", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_scim_token)])
async def create_scim_user(
    payload: ScimUserCreate,
    session: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    email = payload.userName.lower()
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user:
        user.is_active = payload.active if payload.active is not None else user.is_active
    else:
        user = User(
            email=email,
            hashed_password=hash_password(secrets.token_urlsafe(16)),
            full_name=" ".join(
                filter(None, [payload.name.givenName if payload.name else None, payload.name.familyName if payload.name else None])
            )
            or None,
            company_name=None,
            is_active=payload.active if payload.active is not None else True,
            tier=UserTier.ENTERPRISE,
        )
        session.add(user)
        await session.flush()

    team = await _get_or_create_default_team(session, owner_id=user.id)
    role = _resolve_role(payload.groups)

    membership_result = await session.execute(
        select(TeamMember).where(
            TeamMember.team_id == team.id,
            TeamMember.user_id == user.id,
        )
    )
    membership = membership_result.scalar_one_or_none()
    if not membership:
        membership = TeamMember(
            team_id=team.id,
            user_id=user.id,
            role=role,
            accepted_at=datetime.utcnow(),
        )
        session.add(membership)
    else:
        membership.role = role

    await log_audit_event(
        session,
        user_id=user.id,
        entity_type="scim_user",
        entity_id=user.id,
        action="scim.user.provisioned",
        metadata={"email": user.email, "role": role.value},
    )
    await session.commit()
    await session.refresh(user)
    return _scim_user_resource(user)


@router.patch(
    "/Users/{user_id}",
    dependencies=[Depends(require_scim_token)],
)
async def update_scim_user(
    user_id: int,
    payload: ScimUserPatch,
    session: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.active is not None:
        user.is_active = payload.active

    await log_audit_event(
        session,
        user_id=user.id,
        entity_type="scim_user",
        entity_id=user.id,
        action="scim.user.updated",
        metadata={"active": user.is_active},
    )
    await session.commit()
    await session.refresh(user)
    return _scim_user_resource(user)


@router.get("/Groups", response_model=ScimListResponse, dependencies=[Depends(require_scim_token)])
async def list_scim_groups(
    session: AsyncSession = Depends(get_session),
) -> ScimListResponse:
    result = await session.execute(select(Team))
    teams = result.scalars().all()
    resources = [_scim_group_resource(team) for team in teams]
    return ScimListResponse(
        schemas=["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        totalResults=len(resources),
        startIndex=1,
        itemsPerPage=len(resources),
        Resources=resources,
    )


@router.post("/Groups", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_scim_token)])
async def create_scim_group(
    payload: ScimGroupCreate,
    session: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    if not payload.members:
        raise HTTPException(status_code=400, detail="Group members required")

    owner_id = int(payload.members[0].get("value", 0) or 0)
    if not owner_id:
        raise HTTPException(status_code=400, detail="Owner user id required")

    team = Team(
        name=payload.displayName,
        description="Provisioned via SCIM",
        owner_id=owner_id,
        settings={},
    )
    session.add(team)
    await session.flush()

    await log_audit_event(
        session,
        user_id=owner_id,
        entity_type="scim_group",
        entity_id=team.id,
        action="scim.group.created",
        metadata={"name": team.name},
    )
    await session.commit()
    await session.refresh(team)
    return _scim_group_resource(team)
