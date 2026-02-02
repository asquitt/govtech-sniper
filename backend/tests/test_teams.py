"""
RFP Sniper - Teams & Collaboration Tests
=========================================
Tests for team management and collaboration features.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.proposal import Proposal, ProposalSection


class TestTeamManagement:
    """Tests for team CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_team_success(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test creating a new team."""
        response = await client.post(
            "/api/v1/teams/",
            headers=auth_headers,
            json={
                "name": "Proposal Team Alpha",
                "description": "Our main proposal team",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Proposal Team Alpha"
        assert data["your_role"] == "owner"
        assert data["member_count"] == 1

    @pytest.mark.asyncio
    async def test_list_teams(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test listing user's teams."""
        # Create a team first
        await client.post(
            "/api/v1/teams/",
            headers=auth_headers,
            json={"name": "Test Team", "description": "Test"},
        )

        response = await client.get(
            "/api/v1/teams/",
            headers=auth_headers,
        )
        assert response.status_code == 200
        teams = response.json()
        assert len(teams) >= 1
        assert any(t["name"] == "Test Team" for t in teams)

    @pytest.mark.asyncio
    async def test_get_team_details(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test getting team details."""
        # Create team
        create_response = await client.post(
            "/api/v1/teams/",
            headers=auth_headers,
            json={"name": "Details Team", "description": "Test details"},
        )
        team_id = create_response.json()["id"]

        # Get details
        response = await client.get(
            f"/api/v1/teams/{team_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Details Team"
        assert len(data["members"]) == 1
        assert data["members"][0]["role"] == "owner"

    @pytest.mark.asyncio
    async def test_get_team_not_member(
        self, client: AsyncClient, db_session: AsyncSession, auth_headers: dict
    ):
        """Test accessing team when not a member."""
        from app.api.routes.teams import Team

        # Create team owned by someone else
        other_team = Team(
            name="Other Team",
            description="Not your team",
            owner_id=99999,
        )
        db_session.add(other_team)
        await db_session.commit()
        await db_session.refresh(other_team)

        response = await client.get(
            f"/api/v1/teams/{other_team.id}",
            headers=auth_headers,
        )
        assert response.status_code == 403


class TestTeamInvitations:
    """Tests for team invitation system."""

    @pytest.mark.asyncio
    async def test_invite_existing_user(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test inviting an existing user to team."""
        from app.services.auth_service import hash_password

        # Create another user
        new_user = User(
            email="invitee@example.com",
            hashed_password=hash_password("TestPass123!"),
            full_name="Invitee User",
            tier="free",
            is_active=True,
        )
        db_session.add(new_user)
        await db_session.commit()

        # Create team
        team_response = await client.post(
            "/api/v1/teams/",
            headers=auth_headers,
            json={"name": "Invite Test Team"},
        )
        team_id = team_response.json()["id"]

        # Invite user
        response = await client.post(
            f"/api/v1/teams/{team_id}/invite",
            headers=auth_headers,
            json={"email": "invitee@example.com", "role": "member"},
        )
        assert response.status_code == 200
        assert "added to team" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_invite_nonexistent_user(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test inviting a non-existing user creates invitation."""
        # Create team
        team_response = await client.post(
            "/api/v1/teams/",
            headers=auth_headers,
            json={"name": "Invitation Team"},
        )
        team_id = team_response.json()["id"]

        # Invite non-existing user
        response = await client.post(
            f"/api/v1/teams/{team_id}/invite",
            headers=auth_headers,
            json={"email": "newuser@example.com", "role": "member"},
        )
        assert response.status_code == 200
        assert "invitation" in response.json()["message"].lower()
        assert "invitation_token" in response.json()

    @pytest.mark.asyncio
    async def test_invite_unauthorized(
        self, client: AsyncClient, db_session: AsyncSession, auth_headers: dict
    ):
        """Test that non-admins cannot invite."""
        from app.api.routes.teams import Team, TeamMember, TeamRole

        # Create team owned by someone else with test user as viewer
        team = Team(
            name="Not My Team",
            owner_id=99999,
        )
        db_session.add(team)
        await db_session.flush()

        # Get test user id from conftest fixture
        from app.services.auth_service import decode_access_token
        from app.api.deps import get_current_user

        member = TeamMember(
            team_id=team.id,
            user_id=1,  # Assuming test user id is 1
            role=TeamRole.VIEWER,  # Viewer cannot invite
        )
        db_session.add(member)
        await db_session.commit()

        response = await client.post(
            f"/api/v1/teams/{team.id}/invite",
            headers=auth_headers,
            json={"email": "someone@example.com", "role": "member"},
        )
        assert response.status_code == 403


class TestTeamMemberManagement:
    """Tests for team member management."""

    @pytest.mark.asyncio
    async def test_remove_member(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test removing a member from team."""
        from app.services.auth_service import hash_password
        from app.api.routes.teams import TeamMember

        # Create another user
        member_user = User(
            email="member@example.com",
            hashed_password=hash_password("TestPass123!"),
            full_name="Member User",
            tier="free",
            is_active=True,
        )
        db_session.add(member_user)
        await db_session.commit()
        await db_session.refresh(member_user)

        # Create team
        team_response = await client.post(
            "/api/v1/teams/",
            headers=auth_headers,
            json={"name": "Removal Test Team"},
        )
        team_id = team_response.json()["id"]

        # Add member directly
        await client.post(
            f"/api/v1/teams/{team_id}/invite",
            headers=auth_headers,
            json={"email": "member@example.com", "role": "member"},
        )

        # Remove member
        response = await client.delete(
            f"/api/v1/teams/{team_id}/members/{member_user.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "removed" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_cannot_remove_owner(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User,
    ):
        """Test that team owner cannot be removed."""
        # Create team
        team_response = await client.post(
            "/api/v1/teams/",
            headers=auth_headers,
            json={"name": "Owner Team"},
        )
        team_id = team_response.json()["id"]

        # Try to remove owner
        response = await client.delete(
            f"/api/v1/teams/{team_id}/members/{test_user.id}",
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "owner" in response.json()["detail"].lower()


class TestProposalComments:
    """Tests for proposal section comments."""

    @pytest.mark.asyncio
    async def test_add_comment(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_proposal: Proposal,
    ):
        """Test adding a comment to a section."""
        # Create a section
        section = ProposalSection(
            proposal_id=test_proposal.id,
            title="Test Section",
            section_number="1.0",
        )
        db_session.add(section)
        await db_session.commit()
        await db_session.refresh(section)

        response = await client.post(
            f"/api/v1/teams/proposals/{test_proposal.id}/sections/{section.id}/comments",
            headers=auth_headers,
            json={"content": "This looks great!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "This looks great!"
        assert data["is_resolved"] is False

    @pytest.mark.asyncio
    async def test_list_comments(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_proposal: Proposal,
    ):
        """Test listing comments on a section."""
        from app.api.routes.teams import ProposalComment

        # Create section
        section = ProposalSection(
            proposal_id=test_proposal.id,
            title="Comment Section",
            section_number="2.0",
        )
        db_session.add(section)
        await db_session.flush()

        # Add comments
        for i in range(3):
            comment = ProposalComment(
                proposal_section_id=section.id,
                user_id=1,
                content=f"Comment {i+1}",
            )
            db_session.add(comment)
        await db_session.commit()

        response = await client.get(
            f"/api/v1/teams/proposals/{test_proposal.id}/sections/{section.id}/comments",
            headers=auth_headers,
        )
        assert response.status_code == 200
        comments = response.json()
        assert len(comments) == 3

    @pytest.mark.asyncio
    async def test_reply_to_comment(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_proposal: Proposal,
    ):
        """Test replying to a comment."""
        from app.api.routes.teams import ProposalComment

        # Create section and parent comment
        section = ProposalSection(
            proposal_id=test_proposal.id,
            title="Thread Section",
            section_number="3.0",
        )
        db_session.add(section)
        await db_session.flush()

        parent_comment = ProposalComment(
            proposal_section_id=section.id,
            user_id=1,
            content="Parent comment",
        )
        db_session.add(parent_comment)
        await db_session.commit()
        await db_session.refresh(parent_comment)

        # Reply
        response = await client.post(
            f"/api/v1/teams/proposals/{test_proposal.id}/sections/{section.id}/comments",
            headers=auth_headers,
            json={"content": "Reply comment", "parent_id": parent_comment.id},
        )
        assert response.status_code == 200
        assert response.json()["parent_id"] == parent_comment.id

    @pytest.mark.asyncio
    async def test_resolve_comment(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_proposal: Proposal,
    ):
        """Test resolving a comment."""
        from app.api.routes.teams import ProposalComment

        # Create section and comment
        section = ProposalSection(
            proposal_id=test_proposal.id,
            title="Resolve Section",
            section_number="4.0",
        )
        db_session.add(section)
        await db_session.flush()

        comment = ProposalComment(
            proposal_section_id=section.id,
            user_id=1,
            content="Needs fixing",
        )
        db_session.add(comment)
        await db_session.commit()
        await db_session.refresh(comment)

        # Resolve
        response = await client.post(
            f"/api/v1/teams/comments/{comment.id}/resolve",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "resolved" in response.json()["message"]
