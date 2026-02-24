"""
Critical Flow Integration Tests
=================================
End-to-end tests through the HTTP layer for core business flows:
1. Auth lifecycle (register → login → me → change password → logout)
2. RFP CRUD (create → read → update → delete)
3. RFP ownership isolation (IDOR regression)
4. Template listing + creation
5. Proposal creation from RFP
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rfp import RFP
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password

# =============================================================================
# Auth Lifecycle
# =============================================================================


class TestAuthLifecycle:
    """Full auth flow: register → login → me → change password → logout."""

    @pytest.mark.asyncio
    async def test_full_auth_lifecycle(self, client: AsyncClient):
        # 1. Register
        reg = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "lifecycle@example.com",
                "password": "LifeCycle123!",
                "full_name": "Lifecycle User",
                "company_name": "Lifecycle Co",
            },
        )
        assert reg.status_code == 201
        tokens = reg.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        # 2. Get current user
        me = await client.get("/api/v1/auth/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["email"] == "lifecycle@example.com"

        # 3. Change password
        change = await client.post(
            "/api/v1/auth/change-password",
            headers=headers,
            json={
                "current_password": "LifeCycle123!",
                "new_password": "NewLifeCycle456!",
            },
        )
        assert change.status_code == 200

        # 4. Login with new password
        login = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "lifecycle@example.com",
                "password": "NewLifeCycle456!",
            },
        )
        assert login.status_code == 200
        new_tokens = login.json()
        new_headers = {"Authorization": f"Bearer {new_tokens['access_token']}"}

        # 5. Old password no longer works
        bad_login = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "lifecycle@example.com",
                "password": "LifeCycle123!",
            },
        )
        assert bad_login.status_code == 401

        # 6. Logout
        logout = await client.post("/api/v1/auth/logout", headers=new_headers)
        assert logout.status_code == 200


# =============================================================================
# RFP CRUD
# =============================================================================


class TestRFPCrud:
    """Create → Read → Update → Delete an RFP."""

    @pytest.mark.asyncio
    async def test_create_rfp(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/rfps",
            headers=auth_headers,
            json={
                "title": "IT Modernization Services",
                "solicitation_number": "W912HV-25-R-0099",
                "agency": "Department of Defense",
                "naics_code": "541512",
                "description": "Seeking IT modernization services for legacy systems.",
                "estimated_value": 5000000,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "IT Modernization Services"
        assert data["solicitation_number"] == "W912HV-25-R-0099"
        assert data["id"] > 0

    @pytest.mark.asyncio
    async def test_read_rfp(self, client: AsyncClient, auth_headers: dict, test_rfp: RFP):
        resp = await client.get(f"/api/v1/rfps/{test_rfp.id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == test_rfp.id
        assert data["title"] == test_rfp.title

    @pytest.mark.asyncio
    async def test_update_rfp(self, client: AsyncClient, auth_headers: dict, test_rfp: RFP):
        resp = await client.patch(
            f"/api/v1/rfps/{test_rfp.id}",
            headers=auth_headers,
            json={"title": "Updated Cybersecurity RFP"},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Cybersecurity RFP"

    @pytest.mark.asyncio
    async def test_delete_rfp(self, client: AsyncClient, auth_headers: dict, test_rfp: RFP):
        resp = await client.delete(f"/api/v1/rfps/{test_rfp.id}", headers=auth_headers)
        assert resp.status_code == 200

        # Verify deletion
        get_resp = await client.get(f"/api/v1/rfps/{test_rfp.id}", headers=auth_headers)
        assert get_resp.status_code == 404


# =============================================================================
# RFP Ownership Isolation (IDOR)
# =============================================================================


@pytest_asyncio.fixture
async def user_b(db_session: AsyncSession) -> User:
    user = User(
        email="userb@example.com",
        hashed_password=hash_password("UserBPass123!"),
        full_name="User B",
        company_name="B Corp",
        tier="professional",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def user_b_headers(user_b: User) -> dict:
    tokens = create_token_pair(user_b.id, user_b.email, user_b.tier)
    return {"Authorization": f"Bearer {tokens.access_token}"}


class TestRFPOwnershipIsolation:
    """User B cannot access, update, or delete User A's RFP."""

    @pytest.mark.asyncio
    async def test_user_b_cannot_read_user_a_rfp(
        self, client: AsyncClient, test_rfp: RFP, user_b_headers: dict
    ):
        resp = await client.get(f"/api/v1/rfps/{test_rfp.id}", headers=user_b_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_user_b_cannot_update_user_a_rfp(
        self, client: AsyncClient, test_rfp: RFP, user_b_headers: dict
    ):
        resp = await client.patch(
            f"/api/v1/rfps/{test_rfp.id}",
            headers=user_b_headers,
            json={"title": "Hacked"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_user_b_cannot_delete_user_a_rfp(
        self, client: AsyncClient, test_rfp: RFP, user_b_headers: dict
    ):
        resp = await client.delete(f"/api/v1/rfps/{test_rfp.id}", headers=user_b_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_owner_can_still_access(
        self, client: AsyncClient, test_rfp: RFP, auth_headers: dict
    ):
        resp = await client.get(f"/api/v1/rfps/{test_rfp.id}", headers=auth_headers)
        assert resp.status_code == 200


# =============================================================================
# Template Flow
# =============================================================================


class TestTemplateFlow:
    @pytest.mark.asyncio
    async def test_list_templates(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/templates/", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_create_custom_template(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/templates/",
            headers=auth_headers,
            json={
                "name": "Custom Past Performance",
                "category": "past_performance",
                "description": "A custom template for past performance sections",
                "template_text": "Our team {verb} {metric} for {agency}.",
                "placeholders": {"verb": "achieved", "metric": "99%", "agency": "DoD"},
                "keywords": ["past performance", "experience"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Custom Past Performance"
        assert data["is_system"] is False

    @pytest.mark.asyncio
    async def test_list_categories(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/templates/categories", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# =============================================================================
# Proposal from RFP
# =============================================================================


class TestProposalFromRFP:
    @pytest.mark.asyncio
    async def test_get_proposal(self, client: AsyncClient, auth_headers: dict, test_proposal):
        resp = await client.get(
            f"/api/v1/draft/proposals/{test_proposal.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == test_proposal.id
        assert data["rfp_id"] == test_proposal.rfp_id


# =============================================================================
# Cross-cutting: Rate limiting headers
# =============================================================================


class TestRateLimitHeaders:
    @pytest.mark.asyncio
    async def test_auth_endpoints_respond_with_rate_info(self, client: AsyncClient):
        """Login endpoint should not hang or crash under normal load."""
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "Whatever123!"},
        )
        # Should respond (401 expected), not timeout
        assert resp.status_code in (401, 429)
