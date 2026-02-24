"""
Integration tests for scim.py:
  - GET  /scim/v2/Users
  - POST /scim/v2/Users
  - PATCH /scim/v2/Users/{id}
  - GET  /scim/v2/Groups
  - POST /scim/v2/Groups
"""

from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


def scim_headers(token: str = "test-scim-token") -> dict:
    """Build SCIM auth headers."""
    return {"Authorization": f"Bearer {token}"}


class TestScimAuth:
    """SCIM endpoints require a valid bearer token."""

    @pytest.mark.asyncio
    async def test_no_auth_returns_401(self, client: AsyncClient):
        response = await client.get("/api/v1/scim/v2/Users")
        assert response.status_code in (401, 503)

    @pytest.mark.asyncio
    async def test_bad_token_returns_401(self, client: AsyncClient):
        response = await client.get(
            "/api/v1/scim/v2/Users",
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert response.status_code in (401, 503)

    @pytest.mark.asyncio
    @patch("app.api.routes.scim.settings")
    async def test_scim_not_configured_returns_503(self, mock_settings, client: AsyncClient):
        mock_settings.scim_bearer_token = None
        response = await client.get(
            "/api/v1/scim/v2/Users",
            headers=scim_headers(),
        )
        assert response.status_code == 503


class TestListScimUsers:
    """Tests for GET /api/v1/scim/v2/Users."""

    @pytest.mark.asyncio
    @patch("app.api.routes.scim.settings")
    async def test_list_users(
        self,
        mock_settings,
        client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
    ):
        mock_settings.scim_bearer_token = "test-scim-token"
        response = await client.get("/api/v1/scim/v2/Users", headers=scim_headers())
        assert response.status_code == 200
        data = response.json()
        assert data["totalResults"] >= 1
        assert data["schemas"] == ["urn:ietf:params:scim:api:messages:2.0:ListResponse"]


class TestCreateScimUser:
    """Tests for POST /api/v1/scim/v2/Users."""

    @pytest.mark.asyncio
    @patch("app.api.routes.scim.settings")
    async def test_create_user(
        self,
        mock_settings,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        mock_settings.scim_bearer_token = "test-scim-token"
        mock_settings.scim_default_team_name = "Default Team"
        mock_settings.scim_default_role = "member"
        mock_settings.scim_auto_create_team = True
        mock_settings.scim_group_role_map = None

        response = await client.post(
            "/api/v1/scim/v2/Users",
            headers=scim_headers(),
            json={
                "userName": "scim-user@example.com",
                "active": True,
                "name": {"givenName": "SCIM", "familyName": "User"},
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["userName"] == "scim-user@example.com"
        assert data["active"] is True

    @pytest.mark.asyncio
    @patch("app.api.routes.scim.settings")
    async def test_create_existing_user_updates(
        self,
        mock_settings,
        client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
    ):
        mock_settings.scim_bearer_token = "test-scim-token"
        mock_settings.scim_default_team_name = "Default Team"
        mock_settings.scim_default_role = "member"
        mock_settings.scim_auto_create_team = True
        mock_settings.scim_group_role_map = None

        response = await client.post(
            "/api/v1/scim/v2/Users",
            headers=scim_headers(),
            json={
                "userName": test_user.email,
                "active": True,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["userName"] == test_user.email


class TestUpdateScimUser:
    """Tests for PATCH /api/v1/scim/v2/Users/{id}."""

    @pytest.mark.asyncio
    @patch("app.api.routes.scim.settings")
    async def test_update_user(
        self,
        mock_settings,
        client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
    ):
        mock_settings.scim_bearer_token = "test-scim-token"

        response = await client.patch(
            f"/api/v1/scim/v2/Users/{test_user.id}",
            headers=scim_headers(),
            json={"active": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["active"] is False

    @pytest.mark.asyncio
    @patch("app.api.routes.scim.settings")
    async def test_update_user_not_found(
        self,
        mock_settings,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        mock_settings.scim_bearer_token = "test-scim-token"

        response = await client.patch(
            "/api/v1/scim/v2/Users/99999",
            headers=scim_headers(),
            json={"active": False},
        )
        assert response.status_code == 404


class TestListScimGroups:
    """Tests for GET /api/v1/scim/v2/Groups."""

    @pytest.mark.asyncio
    @patch("app.api.routes.scim.settings")
    async def test_list_groups(self, mock_settings, client: AsyncClient, db_session: AsyncSession):
        mock_settings.scim_bearer_token = "test-scim-token"

        response = await client.get("/api/v1/scim/v2/Groups", headers=scim_headers())
        assert response.status_code == 200
        data = response.json()
        assert "totalResults" in data
        assert "Resources" in data


class TestCreateScimGroup:
    """Tests for POST /api/v1/scim/v2/Groups."""

    @pytest.mark.asyncio
    @patch("app.api.routes.scim.settings")
    async def test_create_group(
        self,
        mock_settings,
        client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
    ):
        mock_settings.scim_bearer_token = "test-scim-token"

        response = await client.post(
            "/api/v1/scim/v2/Groups",
            headers=scim_headers(),
            json={
                "displayName": "Engineering",
                "members": [{"value": str(test_user.id)}],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["displayName"] == "Engineering"

    @pytest.mark.asyncio
    @patch("app.api.routes.scim.settings")
    async def test_create_group_no_members(
        self,
        mock_settings,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        mock_settings.scim_bearer_token = "test-scim-token"

        response = await client.post(
            "/api/v1/scim/v2/Groups",
            headers=scim_headers(),
            json={"displayName": "Empty Group"},
        )
        assert response.status_code == 400
