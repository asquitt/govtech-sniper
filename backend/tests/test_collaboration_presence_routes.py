"""
Tests for collaboration/presence routes - Real-time presence and section locking.
"""

import pytest
from httpx import AsyncClient


class TestGetDocumentPresence:
    """Tests for GET /api/v1/collaboration/proposals/{proposal_id}/presence."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        response = await client.get("/api/v1/collaboration/proposals/1/presence")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_presence_returns_structure(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(
            "/api/v1/collaboration/proposals/1/presence",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "proposal_id" in data
        assert "users" in data
        assert "locks" in data


class TestLockSection:
    """Tests for POST /api/v1/collaboration/sections/{section_id}/lock."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        response = await client.post("/api/v1/collaboration/sections/1/lock")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_lock_section_success(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/collaboration/sections/1/lock",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "section_id" in data
        assert "user_id" in data

    @pytest.mark.asyncio
    async def test_lock_already_locked_by_other_user_returns_409(
        self, client: AsyncClient, auth_headers: dict, db_session
    ):
        from app.models.user import User
        from app.services.auth_service import create_token_pair

        # Lock with first user
        await client.post(
            "/api/v1/collaboration/sections/100/lock",
            headers=auth_headers,
        )
        # Create second user to try locking same section
        other = User(
            email="other_locker@example.com",
            hashed_password="hashed",
            full_name="Other",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other)
        await db_session.commit()
        await db_session.refresh(other)
        tokens = create_token_pair(other.id, other.email, other.tier)
        other_headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.post(
            "/api/v1/collaboration/sections/100/lock",
            headers=other_headers,
        )
        assert response.status_code == 409


class TestUnlockSection:
    """Tests for DELETE /api/v1/collaboration/sections/{section_id}/lock."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        response = await client.delete("/api/v1/collaboration/sections/1/lock")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_unlock_not_held_by_other_user_returns_403(
        self, client: AsyncClient, auth_headers: dict, db_session
    ):
        from app.models.user import User
        from app.services.auth_service import create_token_pair

        # Lock with primary user
        await client.post(
            "/api/v1/collaboration/sections/999/lock",
            headers=auth_headers,
        )
        # Try unlocking as different user
        other = User(
            email="other_unlocker@example.com",
            hashed_password="hashed",
            full_name="Other",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other)
        await db_session.commit()
        await db_session.refresh(other)
        tokens = create_token_pair(other.id, other.email, other.tier)
        other_headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.delete(
            "/api/v1/collaboration/sections/999/lock",
            headers=other_headers,
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_lock_and_unlock_success(self, client: AsyncClient, auth_headers: dict):
        # Lock first
        await client.post(
            "/api/v1/collaboration/sections/50/lock",
            headers=auth_headers,
        )
        # Unlock
        response = await client.delete(
            "/api/v1/collaboration/sections/50/lock",
            headers=auth_headers,
        )
        assert response.status_code == 204
