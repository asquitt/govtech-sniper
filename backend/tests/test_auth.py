"""
RFP Sniper - Authentication Tests
=================================
Tests for user registration, login, and token management.
"""

import pyotp
import pytest
from httpx import AsyncClient

from app.models.user import User
from app.services.auth_service import create_token_pair


class TestRegistration:
    """Tests for user registration."""

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        """Test successful user registration."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePass123!",
                "full_name": "New User",
                "company_name": "New Company",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, test_user: User):
        """Test registration with already registered email."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,
                "password": "SecurePass123!",
                "full_name": "Another User",
            },
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_weak_password(self, client: AsyncClient):
        """Test registration with weak password."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak@example.com",
                "password": "weak",
                "full_name": "Weak User",
            },
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        """Test registration with invalid email format."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "SecurePass123!",
                "full_name": "Invalid Email User",
            },
        )
        assert response.status_code == 422  # Validation error


class TestLogin:
    """Tests for user login."""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user: User):
        """Test successful login."""
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
        """Test login with wrong password."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "WrongPassword123!",
            },
        )
        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with non-existent email."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "AnyPassword123!",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_inactive_user(self, client: AsyncClient, db_session, test_user: User):
        """Test login with inactive user account."""
        # Deactivate user
        test_user.is_active = False
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "TestPassword123!",
            },
        )
        assert response.status_code == 403
        assert "deactivated" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_requires_mfa(self, client: AsyncClient, db_session, test_user: User):
        """Test login requires MFA code when enabled."""
        secret = pyotp.random_base32()
        test_user.mfa_secret = secret
        test_user.mfa_enabled = True
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "TestPassword123!",
            },
        )
        assert response.status_code == 401
        assert "MFA" in response.json()["detail"]

        totp = pyotp.TOTP(secret)
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "TestPassword123!",
                "mfa_code": totp.now(),
            },
        )
        assert response.status_code == 200


class TestTokenRefresh:
    """Tests for token refresh."""

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, client: AsyncClient, test_user: User):
        """Test successful token refresh."""
        tokens = create_token_pair(test_user.id, test_user.email, test_user.tier)

        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens.refresh_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, client: AsyncClient):
        """Test refresh with invalid token."""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )
        assert response.status_code == 401


class TestCurrentUser:
    """Tests for current user endpoints."""

    @pytest.mark.asyncio
    async def test_get_me(self, client: AsyncClient, auth_headers: dict, test_user: User):
        """Test getting current user info."""
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["full_name"] == test_user.full_name

    @pytest.mark.asyncio
    async def test_get_me_unauthorized(self, client: AsyncClient):
        """Test getting current user without auth."""
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_invalid_token(self, client: AsyncClient):
        """Test getting current user with invalid token."""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401


class TestPasswordChange:
    """Tests for password change."""

    @pytest.mark.asyncio
    async def test_change_password_success(self, client: AsyncClient, auth_headers: dict):
        """Test successful password change."""
        response = await client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "TestPassword123!",
                "new_password": "NewSecurePass456!",
            },
        )
        assert response.status_code == 200
        assert "successfully" in response.json()["message"]


class TestMFA:
    """Tests for MFA enrollment and verification."""

    @pytest.mark.asyncio
    async def test_mfa_enroll_verify_disable(self, client: AsyncClient, auth_headers: dict):
        enroll = await client.post("/api/v1/auth/mfa/enroll", headers=auth_headers)
        assert enroll.status_code == 200
        payload = enroll.json()
        assert "secret" in payload
        assert "otpauth_url" in payload

        totp = pyotp.TOTP(payload["secret"])
        verify = await client.post(
            "/api/v1/auth/mfa/verify",
            headers=auth_headers,
            json={"code": totp.now()},
        )
        assert verify.status_code == 200

        disable = await client.post(
            "/api/v1/auth/mfa/disable",
            headers=auth_headers,
            json={"code": totp.now()},
        )
        assert disable.status_code == 200

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, client: AsyncClient, auth_headers: dict):
        """Test password change with wrong current password."""
        response = await client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "WrongPassword123!",
                "new_password": "NewSecurePass456!",
            },
        )
        assert response.status_code == 400
        assert "incorrect" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_change_password_weak_new(self, client: AsyncClient, auth_headers: dict):
        """Test password change with weak new password."""
        response = await client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "TestPassword123!",
                "new_password": "weak",
            },
        )
        assert response.status_code == 400


class TestProfile:
    """Tests for user profile management."""

    @pytest.mark.asyncio
    async def test_get_profile(self, client: AsyncClient, auth_headers: dict):
        """Test getting user profile."""
        response = await client.get("/api/v1/auth/profile", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "naics_codes" in data
        assert "clearance_level" in data

    @pytest.mark.asyncio
    async def test_update_profile(self, client: AsyncClient, auth_headers: dict):
        """Test updating user profile."""
        response = await client.put(
            "/api/v1/auth/profile",
            headers=auth_headers,
            json={
                "naics_codes": ["541512", "541511"],
                "preferred_states": ["VA", "MD", "DC"],
                "min_contract_value": 50000,
                "max_contract_value": 5000000,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "profile" in data
        assert data["profile"]["naics_codes"] == ["541512", "541511"]
        assert data["profile"]["preferred_states"] == ["VA", "MD", "DC"]


class TestLogout:
    """Tests for logout."""

    @pytest.mark.asyncio
    async def test_logout_success(self, client: AsyncClient, auth_headers: dict):
        """Test successful logout."""
        response = await client.post("/api/v1/auth/logout", headers=auth_headers)
        assert response.status_code == 200
        assert "logged out" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_logout_unauthorized(self, client: AsyncClient):
        """Test logout without auth."""
        response = await client.post("/api/v1/auth/logout")
        assert response.status_code == 401
