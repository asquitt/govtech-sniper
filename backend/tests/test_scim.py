"""
RFP Sniper - SCIM Provisioning Tests
====================================
Tests for SCIM user and group provisioning.
"""

import json

import pytest
from httpx import AsyncClient
from sqlmodel import select

from app.config import settings
from app.api.routes.teams import TeamMember, Team


class TestScimProvisioning:
    @pytest.mark.asyncio
    async def test_scim_user_create_and_group_mapping(
        self,
        client: AsyncClient,
        db_session,
    ):
        settings.scim_bearer_token = "test-token"
        settings.scim_default_team_name = "GovTech Team"
        settings.scim_group_role_map = json.dumps({"GovTech Admins": "admin"})

        response = await client.post(
            "/api/v1/scim/v2/Users",
            headers={"Authorization": "Bearer test-token"},
            json={
                "userName": "scim-user@example.com",
                "active": True,
                "name": {"givenName": "SCIM", "familyName": "User"},
                "groups": [{"display": "GovTech Admins"}],
            },
        )
        assert response.status_code == 201
        payload = response.json()
        assert payload["userName"] == "scim-user@example.com"

        team_result = await db_session.execute(
            select(Team).where(Team.name == "GovTech Team")
        )
        team = team_result.scalar_one()

        membership_result = await db_session.execute(
            select(TeamMember).where(TeamMember.team_id == team.id)
        )
        membership = membership_result.scalar_one()
        assert membership.role.value == "admin"

        groups = await client.get(
            "/api/v1/scim/v2/Groups",
            headers={"Authorization": "Bearer test-token"},
        )
        assert groups.status_code == 200
        list_payload = groups.json()
        assert list_payload["totalResults"] >= 1
