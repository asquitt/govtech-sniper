"""
RFP Sniper - Teams & Collaboration Routes
==========================================
Team management and collaboration features.
"""

from datetime import datetime
from enum import Enum

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import JSON, Column, Field, SQLModel, Text, select

from app.api.deps import UserAuth, get_current_user
from app.database import get_session
from app.models.user import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/teams", tags=["Teams"])


# =============================================================================
# Team Models
# =============================================================================


class TeamRole(str, Enum):
    """Roles within a team."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class Team(SQLModel, table=True):
    """
    Team/Organization for collaboration.
    """

    __tablename__ = "teams"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=255)
    description: str | None = Field(default=None, max_length=1000)

    # Owner
    owner_id: int = Field(foreign_key="users.id")

    # Settings
    settings: dict = Field(default={}, sa_column=Column(JSON))

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TeamMember(SQLModel, table=True):
    """
    Team membership.
    """

    __tablename__ = "team_members"

    id: int | None = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="teams.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    role: TeamRole = Field(default=TeamRole.MEMBER)

    # Invitation status
    invited_at: datetime = Field(default_factory=datetime.utcnow)
    accepted_at: datetime | None = None
    is_active: bool = Field(default=True)


class TeamInvitation(SQLModel, table=True):
    """
    Pending team invitations.
    """

    __tablename__ = "team_invitations"

    id: int | None = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="teams.id", index=True)
    email: str = Field(max_length=255, index=True)
    role: TeamRole = Field(default=TeamRole.MEMBER)

    # Invitation details
    invited_by: int = Field(foreign_key="users.id")
    token: str = Field(max_length=255, unique=True)
    expires_at: datetime

    # Status
    is_accepted: bool = Field(default=False)
    accepted_at: datetime | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProposalComment(SQLModel, table=True):
    """
    Comments on proposal sections.
    """

    __tablename__ = "proposal_comments"

    id: int | None = Field(default=None, primary_key=True)
    proposal_section_id: int = Field(foreign_key="proposal_sections.id", index=True)
    user_id: int = Field(foreign_key="users.id")

    # Comment content
    content: str = Field(sa_column=Column(Text))

    # Thread support
    parent_id: int | None = Field(default=None, foreign_key="proposal_comments.id")

    # Status
    is_resolved: bool = Field(default=False)
    resolved_by: int | None = Field(default=None, foreign_key="users.id")
    resolved_at: datetime | None = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Request/Response Schemas
# =============================================================================


class TeamCreate(BaseModel):
    """Create a new team."""

    name: str
    description: str | None = None


class TeamUpdate(BaseModel):
    """Update team details."""

    name: str | None = None
    description: str | None = None


class TeamResponse(BaseModel):
    """Team response."""

    id: int
    name: str
    description: str | None
    owner_id: int
    member_count: int
    your_role: str
    created_at: datetime


class InviteRequest(BaseModel):
    """Team invitation request."""

    email: EmailStr
    role: TeamRole = TeamRole.MEMBER


class TeamMemberUpdate(BaseModel):
    """Update a team member's role."""

    role: TeamRole


class CommentCreate(BaseModel):
    """Create a comment."""

    content: str
    parent_id: int | None = None


class CommentResponse(BaseModel):
    """Comment response."""

    id: int
    content: str
    user_id: int
    user_name: str
    parent_id: int | None
    is_resolved: bool
    created_at: datetime


# =============================================================================
# Team Endpoints
# =============================================================================


@router.get("/", response_model=list[TeamResponse])
async def list_teams(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[TeamResponse]:
    """
    List teams the user belongs to.
    """
    # Get user's team memberships
    memberships = await session.execute(
        select(TeamMember, Team)
        .join(Team, TeamMember.team_id == Team.id)
        .where(
            TeamMember.user_id == current_user.id,
            TeamMember.is_active == True,
        )
    )

    teams = []
    for membership, team in memberships.all():
        # Get member count
        count_result = await session.execute(
            select(func.count(TeamMember.id)).where(
                TeamMember.team_id == team.id,
                TeamMember.is_active == True,
            )
        )
        member_count = count_result.scalar() or 0

        teams.append(
            TeamResponse(
                id=team.id,
                name=team.name,
                description=team.description,
                owner_id=team.owner_id,
                member_count=member_count,
                your_role=membership.role.value,
                created_at=team.created_at,
            )
        )

    return teams


@router.post("/", response_model=TeamResponse)
async def create_team(
    request: TeamCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TeamResponse:
    """
    Create a new team.
    """
    # Create team
    team = Team(
        name=request.name,
        description=request.description,
        owner_id=current_user.id,
    )
    session.add(team)
    await session.flush()

    # Add creator as owner
    membership = TeamMember(
        team_id=team.id,
        user_id=current_user.id,
        role=TeamRole.OWNER,
        accepted_at=datetime.utcnow(),
    )
    session.add(membership)
    await session.commit()
    await session.refresh(team)

    logger.info("Team created", team_id=team.id, owner_id=current_user.id)

    return TeamResponse(
        id=team.id,
        name=team.name,
        description=team.description,
        owner_id=team.owner_id,
        member_count=1,
        your_role=TeamRole.OWNER.value,
        created_at=team.created_at,
    )


@router.get("/{team_id}")
async def get_team(
    team_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Get team details including members.
    """
    # Verify membership
    membership = await session.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id,
            TeamMember.is_active == True,
        )
    )
    member = membership.scalar_one_or_none()

    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this team")

    # Get team
    team_result = await session.execute(select(Team).where(Team.id == team_id))
    team = team_result.scalar_one_or_none()

    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Get members with user info
    members_result = await session.execute(
        select(TeamMember, User)
        .join(User, TeamMember.user_id == User.id)
        .where(
            TeamMember.team_id == team_id,
            TeamMember.is_active == True,
        )
    )

    members = [
        {
            "user_id": m.user_id,
            "email": u.email,
            "full_name": u.full_name,
            "role": m.role.value,
            "joined_at": m.accepted_at.isoformat() if m.accepted_at else None,
        }
        for m, u in members_result.all()
    ]

    return {
        "id": team.id,
        "name": team.name,
        "description": team.description,
        "owner_id": team.owner_id,
        "your_role": member.role.value,
        "members": members,
        "created_at": team.created_at,
    }


@router.post("/{team_id}/invite")
async def invite_member(
    team_id: int,
    request: InviteRequest,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Invite a user to the team.
    """
    # Verify permission (owner or admin)
    membership = await session.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id,
            TeamMember.is_active == True,
            TeamMember.role.in_([TeamRole.OWNER, TeamRole.ADMIN]),
        )
    )
    if not membership.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not authorized to invite members")

    # Fetch team for email context
    team_result = await session.execute(select(Team).where(Team.id == team_id))
    team = team_result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Check if user exists
    user_result = await session.execute(select(User).where(User.email == request.email.lower()))
    existing_user = user_result.scalar_one_or_none()

    if existing_user:
        # Check if already a member
        existing_member = await session.execute(
            select(TeamMember).where(
                TeamMember.team_id == team_id,
                TeamMember.user_id == existing_user.id,
            )
        )
        if existing_member.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="User is already a team member")

        # Add directly if user exists
        member = TeamMember(
            team_id=team_id,
            user_id=existing_user.id,
            role=request.role,
            accepted_at=datetime.utcnow(),
        )
        session.add(member)
        await session.commit()

        logger.info("Member added", team_id=team_id, user_id=existing_user.id)

        return {"message": f"User {request.email} added to team"}

    else:
        # Create invitation for non-existing user
        import secrets

        token = secrets.token_urlsafe(32)

        invitation = TeamInvitation(
            team_id=team_id,
            email=request.email.lower(),
            role=request.role,
            invited_by=current_user.id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        session.add(invitation)
        await session.commit()

        # Send invitation email
        await _send_invitation_email(team, request.email, token)
        logger.info("Invitation created and emailed", team_id=team_id, email=request.email)

        return {
            "message": f"Invitation sent to {request.email}",
            "invitation_token": token,
        }


@router.delete("/{team_id}/members/{user_id}")
async def remove_member(
    team_id: int,
    user_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Remove a member from the team.
    """
    # Verify permission
    membership = await session.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id,
            TeamMember.is_active == True,
            TeamMember.role.in_([TeamRole.OWNER, TeamRole.ADMIN]),
        )
    )
    current_member = membership.scalar_one_or_none()

    if not current_member:
        raise HTTPException(status_code=403, detail="Not authorized to remove members")

    # Can't remove owner
    team_result = await session.execute(select(Team).where(Team.id == team_id))
    team = team_result.scalar_one_or_none()

    if team and team.owner_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot remove team owner")

    # Remove member
    target_member = await session.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
        )
    )
    member = target_member.scalar_one_or_none()

    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    member.is_active = False
    await session.commit()

    logger.info("Member removed", team_id=team_id, user_id=user_id)

    return {"message": "Member removed from team"}


@router.patch("/{team_id}/members/{user_id}")
async def update_member_role(
    team_id: int,
    user_id: int,
    request: TeamMemberUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Update a member's role within a team.
    """
    membership_result = await session.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id,
            TeamMember.is_active == True,
            TeamMember.role.in_([TeamRole.OWNER, TeamRole.ADMIN]),
        )
    )
    current_member = membership_result.scalar_one_or_none()
    if not current_member:
        raise HTTPException(status_code=403, detail="Not authorized to update roles")

    member_result = await session.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
        )
    )
    member = member_result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    if member.role == TeamRole.OWNER and request.role != TeamRole.OWNER:
        raise HTTPException(status_code=400, detail="Cannot change owner role")

    if request.role == TeamRole.OWNER and current_member.role != TeamRole.OWNER:
        raise HTTPException(status_code=403, detail="Only the owner can assign owner role")

    member.role = request.role
    await session.commit()
    await session.refresh(member)

    return {"message": "Member role updated", "user_id": user_id, "role": member.role.value}


# =============================================================================
# Comment Endpoints
# =============================================================================


@router.get("/proposals/{proposal_id}/sections/{section_id}/comments")
async def list_comments(
    proposal_id: int,
    section_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[CommentResponse]:
    """
    List comments on a proposal section.
    """
    from app.models.proposal import Proposal, ProposalSection

    # Verify access to proposal
    section_result = await session.execute(
        select(ProposalSection)
        .join(Proposal)
        .where(
            ProposalSection.id == section_id,
            Proposal.id == proposal_id,
        )
    )
    section = section_result.scalar_one_or_none()

    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    # Get comments with user info
    comments_result = await session.execute(
        select(ProposalComment, User)
        .join(User, ProposalComment.user_id == User.id)
        .where(ProposalComment.proposal_section_id == section_id)
        .order_by(ProposalComment.created_at)
    )

    return [
        CommentResponse(
            id=c.id,
            content=c.content,
            user_id=c.user_id,
            user_name=u.full_name or u.email,
            parent_id=c.parent_id,
            is_resolved=c.is_resolved,
            created_at=c.created_at,
        )
        for c, u in comments_result.all()
    ]


@router.post("/proposals/{proposal_id}/sections/{section_id}/comments")
async def add_comment(
    proposal_id: int,
    section_id: int,
    request: CommentCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CommentResponse:
    """
    Add a comment to a proposal section.
    """
    from app.models.proposal import Proposal, ProposalSection

    # Verify access
    section_result = await session.execute(
        select(ProposalSection)
        .join(Proposal)
        .where(
            ProposalSection.id == section_id,
            Proposal.id == proposal_id,
        )
    )
    section = section_result.scalar_one_or_none()

    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    # Create comment
    comment = ProposalComment(
        proposal_section_id=section_id,
        user_id=current_user.id,
        content=request.content,
        parent_id=request.parent_id,
    )
    session.add(comment)
    await session.commit()
    await session.refresh(comment)

    logger.info("Comment added", section_id=section_id, user_id=current_user.id)

    # Get user info
    user_result = await session.execute(select(User).where(User.id == current_user.id))
    user = user_result.scalar_one()

    return CommentResponse(
        id=comment.id,
        content=comment.content,
        user_id=comment.user_id,
        user_name=user.full_name or user.email,
        parent_id=comment.parent_id,
        is_resolved=comment.is_resolved,
        created_at=comment.created_at,
    )


@router.post("/comments/{comment_id}/resolve")
async def resolve_comment(
    comment_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Mark a comment as resolved.
    """
    comment_result = await session.execute(
        select(ProposalComment).where(ProposalComment.id == comment_id)
    )
    comment = comment_result.scalar_one_or_none()

    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    comment.is_resolved = True
    comment.resolved_by = current_user.id
    comment.resolved_at = datetime.utcnow()
    await session.commit()

    return {"message": "Comment resolved"}


# Import needed for member count
from datetime import timedelta

from app.api.routes.notifications import email_service
from app.config import settings


async def _send_invitation_email(team: Team, to_email: str, token: str) -> None:
    """Send a team invitation email via Resend."""
    accept_url = f"{settings.app_url}/teams/accept?token={token}"

    subject = f"You've been invited to join {team.name} on Orbitr"
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #1a365d; color: white; padding: 20px; text-align: center;">
            <h1 style="margin: 0;">Orbitr</h1>
        </div>
        <div style="padding: 20px;">
            <h2>Team Invitation</h2>
            <p>You've been invited to join <strong>{team.name}</strong> on Orbitr.</p>
            {f"<p>{team.description}</p>" if team.description else ""}
            <p>
                <a href="{accept_url}"
                   style="background: #3182ce; color: white; padding: 12px 24px;
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    Accept Invitation
                </a>
            </p>
            <p style="font-size: 12px; color: #666;">This invitation expires in 7 days.</p>
        </div>
        <div style="background: #f7f7f7; padding: 15px; text-align: center; font-size: 12px; color: #666;">
            <p>Orbitr - Government Proposal Automation</p>
        </div>
    </body>
    </html>
    """
    text = (
        f"You've been invited to join {team.name} on Orbitr.\n\n"
        f"Accept invitation: {accept_url}\n\n"
        f"This invitation expires in 7 days."
    )
    await email_service.send_email(to_email, subject, html, text)
