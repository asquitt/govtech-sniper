"""
Tests for auth routes - Registration, login, MFA, profile.
"""

import pyotp
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password


class TestRegister:
    """Tests for POST /api/v1/auth/register."""

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "StrongP@ss1",
                "full_name": "New User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, test_user: User):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,
                "password": "StrongP@ss1",
                "full_name": "Duplicate",
            },
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_weak_password(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak@example.com",
                "password": "123",
                "full_name": "Weak Pass",
            },
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "StrongP@ss1",
                "full_name": "Bad Email",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_missing_full_name(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "no_name@example.com",
                "password": "StrongP@ss1",
            },
        )
        assert response.status_code == 422


class TestLogin:
    """Tests for POST /api/v1/auth/login."""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user: User):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "TestPassword123!",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, test_user: User):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "WrongPassword123!",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nobody@example.com",
                "password": "AnyPassword1!",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_inactive_user(self, client: AsyncClient, db_session: AsyncSession):
        user = User(
            email="inactive@example.com",
            hashed_password=hash_password("StrongP@ss1"),
            full_name="Inactive",
            tier="free",
            is_active=False,
            is_verified=True,
        )
        db_session.add(user)
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "inactive@example.com", "password": "StrongP@ss1"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_login_mfa_required(self, client: AsyncClient, db_session: AsyncSession):
        from app.models.user import UserTier

        secret = pyotp.random_base32()
        user = User(
            email="mfa_user@example.com",
            hashed_password=hash_password("StrongP@ss1"),
            full_name="MFA User",
            tier=UserTier.FREE,
            is_active=True,
            is_verified=True,
            mfa_enabled=True,
            mfa_secret=secret,
        )
        db_session.add(user)
        await db_session.commit()

        # Login without MFA code
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "mfa_user@example.com", "password": "StrongP@ss1"},
        )
        assert response.status_code == 401
        assert "MFA code required" in response.json()["detail"]

        # Login with valid MFA code
        totp = pyotp.TOTP(secret)
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "mfa_user@example.com",
                "password": "StrongP@ss1",
                "mfa_code": totp.now(),
            },
        )
        assert response.status_code == 200
        assert "access_token" in response.json()


class TestRefresh:
    """Tests for POST /api/v1/auth/refresh."""

    @pytest.mark.asyncio
    async def test_refresh_success(self, client: AsyncClient, test_user: User):
        tokens = create_token_pair(test_user.id, test_user.email, test_user.tier)
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens.refresh_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )
        assert response.status_code == 401


class TestLogout:
    """Tests for POST /api/v1/auth/logout."""

    @pytest.mark.asyncio
    async def test_logout_unauthenticated(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/logout")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_success(self, client: AsyncClient, auth_headers: dict):
        response = await client.post("/api/v1/auth/logout", headers=auth_headers)
        assert response.status_code == 200
        assert "logged out" in response.json()["message"].lower()


class TestGetMe:
    """Tests for GET /api/v1/auth/me."""

    @pytest.mark.asyncio
    async def test_me_unauthenticated(self, client: AsyncClient):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_me_success(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "email" in data
        assert "tier" in data
        assert "mfa_enabled" in data


class TestUpdateMe:
    """Tests for PUT /api/v1/auth/me."""

    @pytest.mark.asyncio
    async def test_update_me_unauthenticated(self, client: AsyncClient):
        response = await client.put(
            "/api/v1/auth/me",
            params={"full_name": "Updated"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_me_success(self, client: AsyncClient, auth_headers: dict):
        response = await client.put(
            "/api/v1/auth/me",
            headers=auth_headers,
            params={"full_name": "Updated Name", "company_name": "NewCo"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"
        assert data["company_name"] == "NewCo"


class TestChangePassword:
    """Tests for POST /api/v1/auth/change-password."""

    @pytest.mark.asyncio
    async def test_change_password_unauthenticated(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "old", "new_password": "new"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={"current_password": "WrongPass!", "new_password": "NewStrongP@ss1"},
        )
        assert response.status_code == 400
        assert "incorrect" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_change_password_weak_new(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={"current_password": "TestPassword123!", "new_password": "123"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_change_password_success(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "TestPassword123!",
                "new_password": "NewStrongP@ss2",
            },
        )
        assert response.status_code == 200


class TestMfaEnroll:
    """Tests for POST /api/v1/auth/mfa/enroll."""

    @pytest.mark.asyncio
    async def test_enroll_unauthenticated(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/mfa/enroll")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_enroll_success(self, client: AsyncClient, auth_headers: dict):
        response = await client.post("/api/v1/auth/mfa/enroll", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "secret" in data
        assert "otpauth_url" in data


class TestProfile:
    """Tests for GET/PUT /api/v1/auth/profile."""

    @pytest.mark.asyncio
    async def test_get_profile_unauthenticated(self, client: AsyncClient):
        response = await client.get("/api/v1/auth/profile")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_profile_creates_default(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/auth/profile", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["clearance_level"] == "none"
        assert data["naics_codes"] == []

    @pytest.mark.asyncio
    async def test_update_profile_success(self, client: AsyncClient, auth_headers: dict):
        response = await client.put(
            "/api/v1/auth/profile",
            headers=auth_headers,
            json={
                "naics_codes": ["541511", "541512"],
                "preferred_states": ["VA", "MD"],
                "min_contract_value": 100000,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "541511" in data["profile"]["naics_codes"]
        assert data["profile"]["min_contract_value"] == 100000
