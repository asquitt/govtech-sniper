"""
Integration tests for teams.py — /teams/ CRUD, invite, members, comments
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.teams import ProposalComment
from app.models.proposal import Proposal, ProposalSection
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password


async def _create_second_user(db_session: AsyncSession) -> tuple[User, dict]:
    user2 = User(
        email="other@example.com",
        hashed_password=hash_password("OtherPass123!"),
        full_name="Other User",
        company_name="Other Co",
        tier="professional",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user2)
    await db_session.commit()
    await db_session.refresh(user2)
    tokens = create_token_pair(user2.id, user2.email, user2.tier)
    return user2, {"Authorization": f"Bearer {tokens.access_token}"}


class TestListTeams:
    """GET /api/v1/teams/"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/teams/")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_list(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.get("/api/v1/teams/", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []


class TestCreateTeam:
    """POST /api/v1/teams/"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/teams/", json={"name": "Test Team"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_team(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.post(
            "/api/v1/teams/",
            headers=auth_headers,
            json={"name": "Alpha Team", "description": "Our first team"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Alpha Team"
        assert data["your_role"] == "owner"
        assert data["member_count"] == 1

    @pytest.mark.asyncio
    async def test_create_team_appears_in_list(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        await client.post("/api/v1/teams/", headers=auth_headers, json={"name": "Listed Team"})
        response = await client.get("/api/v1/teams/", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["name"] == "Listed Team"


class TestGetTeam:
    """GET /api/v1/teams/{team_id}"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/teams/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_team(self, client: AsyncClient, auth_headers: dict, test_user: User):
        create_response = await client.post(
            "/api/v1/teams/", headers=auth_headers, json={"name": "Detail Team"}
        )
        team_id = create_response.json()["id"]

        response = await client.get(f"/api/v1/teams/{team_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Detail Team"
        assert len(data["members"]) == 1

    @pytest.mark.asyncio
    async def test_get_team_not_member(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        user2, headers2 = await _create_second_user(db_session)
        create_response = await client.post(
            "/api/v1/teams/", headers=headers2, json={"name": "Private Team"}
        )
        team_id = create_response.json()["id"]

        response = await client.get(f"/api/v1/teams/{team_id}", headers=auth_headers)
        assert response.status_code == 403


class TestInviteMember:
    """POST /api/v1/teams/{team_id}/invite"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/teams/1/invite", json={"email": "x@example.com"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invite_existing_user(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        user2, _ = await _create_second_user(db_session)
        create_response = await client.post(
            "/api/v1/teams/", headers=auth_headers, json={"name": "Invite Team"}
        )
        team_id = create_response.json()["id"]

        response = await client.post(
            f"/api/v1/teams/{team_id}/invite",
            headers=auth_headers,
            json={"email": "other@example.com", "role": "member"},
        )
        assert response.status_code == 200
        assert "added to team" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_invite_duplicate_member(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        user2, _ = await _create_second_user(db_session)
        create_response = await client.post(
            "/api/v1/teams/", headers=auth_headers, json={"name": "Dupe Team"}
        )
        team_id = create_response.json()["id"]

        await client.post(
            f"/api/v1/teams/{team_id}/invite",
            headers=auth_headers,
            json={"email": "other@example.com"},
        )
        # Second invite should fail
        response = await client.post(
            f"/api/v1/teams/{team_id}/invite",
            headers=auth_headers,
            json={"email": "other@example.com"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_invite_non_admin(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        user2, headers2 = await _create_second_user(db_session)
        # user2 creates team
        create_response = await client.post(
            "/api/v1/teams/", headers=headers2, json={"name": "U2 Team"}
        )
        team_id = create_response.json()["id"]

        # test_user (not a member) tries to invite
        response = await client.post(
            f"/api/v1/teams/{team_id}/invite",
            headers=auth_headers,
            json={"email": "someone@example.com"},
        )
        assert response.status_code == 403


class TestRemoveMember:
    """DELETE /api/v1/teams/{team_id}/members/{user_id}"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.delete("/api/v1/teams/1/members/2")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_remove_member(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        user2, _ = await _create_second_user(db_session)
        create_response = await client.post(
            "/api/v1/teams/", headers=auth_headers, json={"name": "Remove Team"}
        )
        team_id = create_response.json()["id"]

        await client.post(
            f"/api/v1/teams/{team_id}/invite",
            headers=auth_headers,
            json={"email": "other@example.com"},
        )

        response = await client.delete(
            f"/api/v1/teams/{team_id}/members/{user2.id}", headers=auth_headers
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_cannot_remove_owner(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        create_response = await client.post(
            "/api/v1/teams/", headers=auth_headers, json={"name": "Owner Team"}
        )
        team_id = create_response.json()["id"]

        response = await client.delete(
            f"/api/v1/teams/{team_id}/members/{test_user.id}", headers=auth_headers
        )
        assert response.status_code == 400


class TestUpdateMemberRole:
    """PATCH /api/v1/teams/{team_id}/members/{user_id}"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.patch("/api/v1/teams/1/members/2", json={"role": "admin"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_role(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        user2, _ = await _create_second_user(db_session)
        create_response = await client.post(
            "/api/v1/teams/", headers=auth_headers, json={"name": "Role Team"}
        )
        team_id = create_response.json()["id"]
        await client.post(
            f"/api/v1/teams/{team_id}/invite",
            headers=auth_headers,
            json={"email": "other@example.com"},
        )

        response = await client.patch(
            f"/api/v1/teams/{team_id}/members/{user2.id}",
            headers=auth_headers,
            json={"role": "admin"},
        )
        assert response.status_code == 200
        assert response.json()["role"] == "admin"


class TestResolveComment:
    """POST /api/v1/teams/comments/{comment_id}/resolve"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/teams/comments/1/resolve")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_resolve_comment(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
        test_proposal: Proposal,
    ):
        section = ProposalSection(
            proposal_id=test_proposal.id,
            title="Test Section",
            section_type="technical",
            section_number="1.0",
            order_index=0,
        )
        db_session.add(section)
        await db_session.flush()

        comment = ProposalComment(
            proposal_section_id=section.id,
            user_id=test_user.id,
            content="Needs revision",
        )
        db_session.add(comment)
        await db_session.commit()
        await db_session.refresh(comment)

        response = await client.post(
            f"/api/v1/teams/comments/{comment.id}/resolve", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Comment resolved"

    @pytest.mark.asyncio
    async def test_resolve_not_found(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.post("/api/v1/teams/comments/99999/resolve", headers=auth_headers)
        assert response.status_code == 404
