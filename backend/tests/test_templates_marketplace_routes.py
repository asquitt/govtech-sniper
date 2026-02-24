"""
Integration tests for templates_marketplace.py:
  - GET  /templates/marketplace
  - GET  /templates/marketplace/popular
  - POST /templates/{id}/publish
  - POST /templates/{id}/fork
  - POST /templates/{id}/rate
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.templates.models import ProposalTemplate
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password


@pytest.fixture
async def user_template(db_session: AsyncSession, test_user: User) -> ProposalTemplate:
    """Create a private user template for marketplace tests."""
    t = ProposalTemplate(
        name="My Private Template",
        category="Technical",
        description="Private template for testing.",
        template_text="Template body {var}",
        placeholders={"var": "value"},
        keywords=["test"],
        is_system=False,
        is_public=False,
        user_id=test_user.id,
    )
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    return t


@pytest.fixture
async def public_template(db_session: AsyncSession, test_user: User) -> ProposalTemplate:
    """Create a public template for marketplace tests."""
    t = ProposalTemplate(
        name="Public Template",
        category="Technical",
        description="A public template.",
        template_text="Public body {var}",
        placeholders={"var": "value"},
        keywords=["public"],
        is_system=False,
        is_public=True,
        user_id=test_user.id,
    )
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    return t


class TestBrowseMarketplace:
    """Tests for GET /api/v1/templates/marketplace."""

    @pytest.mark.asyncio
    async def test_browse_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/templates/marketplace")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_browse_empty(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.get("/api/v1/templates/marketplace", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_browse_returns_public(
        self,
        client: AsyncClient,
        auth_headers: dict,
        public_template: ProposalTemplate,
        test_user: User,
    ):
        response = await client.get("/api/v1/templates/marketplace", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        names = [t["name"] for t in data["items"]]
        assert "Public Template" in names

    @pytest.mark.asyncio
    async def test_browse_excludes_private(
        self,
        client: AsyncClient,
        auth_headers: dict,
        user_template: ProposalTemplate,
        test_user: User,
    ):
        response = await client.get("/api/v1/templates/marketplace", headers=auth_headers)
        assert response.status_code == 200
        names = [t["name"] for t in response.json()["items"]]
        assert "My Private Template" not in names

    @pytest.mark.asyncio
    async def test_browse_with_search(
        self,
        client: AsyncClient,
        auth_headers: dict,
        public_template: ProposalTemplate,
        test_user: User,
    ):
        response = await client.get(
            "/api/v1/templates/marketplace?q=Public",
            headers=auth_headers,
        )
        assert response.status_code == 200


class TestPopularTemplates:
    """Tests for GET /api/v1/templates/marketplace/popular."""

    @pytest.mark.asyncio
    async def test_popular_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/templates/marketplace/popular")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_popular_success(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.get("/api/v1/templates/marketplace/popular", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestPublishTemplate:
    """Tests for POST /api/v1/templates/{id}/publish."""

    @pytest.mark.asyncio
    async def test_publish_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/templates/1/publish")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_publish_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        user_template: ProposalTemplate,
        test_user: User,
    ):
        response = await client.post(
            f"/api/v1/templates/{user_template.id}/publish",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["is_public"] is True

    @pytest.mark.asyncio
    async def test_publish_not_found(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.post("/api/v1/templates/99999/publish", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_publish_idor(
        self,
        client: AsyncClient,
        user_template: ProposalTemplate,
        db_session: AsyncSession,
    ):
        other = User(
            email="other@example.com",
            hashed_password=hash_password("OtherPass123!"),
            full_name="Other",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other)
        await db_session.commit()
        await db_session.refresh(other)
        tokens = create_token_pair(other.id, other.email, other.tier)
        headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.post(
            f"/api/v1/templates/{user_template.id}/publish",
            headers=headers,
        )
        assert response.status_code == 403


class TestForkTemplate:
    """Tests for POST /api/v1/templates/{id}/fork."""

    @pytest.mark.asyncio
    async def test_fork_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/templates/1/fork")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_fork_public_template(
        self,
        client: AsyncClient,
        auth_headers: dict,
        public_template: ProposalTemplate,
        test_user: User,
    ):
        response = await client.post(
            f"/api/v1/templates/{public_template.id}/fork",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["forked_from_id"] == public_template.id
        assert "(Fork)" in data["name"]

    @pytest.mark.asyncio
    async def test_fork_private_template_other_user(
        self,
        client: AsyncClient,
        user_template: ProposalTemplate,
        db_session: AsyncSession,
    ):
        other = User(
            email="other2@example.com",
            hashed_password=hash_password("OtherPass123!"),
            full_name="Other",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other)
        await db_session.commit()
        await db_session.refresh(other)
        tokens = create_token_pair(other.id, other.email, other.tier)
        headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.post(
            f"/api/v1/templates/{user_template.id}/fork",
            headers=headers,
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_fork_not_found(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.post("/api/v1/templates/99999/fork", headers=auth_headers)
        assert response.status_code == 404


class TestRateTemplate:
    """Tests for POST /api/v1/templates/{id}/rate."""

    @pytest.mark.asyncio
    async def test_rate_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/templates/1/rate", json={"rating": 5})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_rate_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        public_template: ProposalTemplate,
        test_user: User,
    ):
        response = await client.post(
            f"/api/v1/templates/{public_template.id}/rate",
            headers=auth_headers,
            json={"rating": 4},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["average_rating"] == 4.0
        assert data["total_ratings"] == 1

    @pytest.mark.asyncio
    async def test_rate_invalid_rating(
        self,
        client: AsyncClient,
        auth_headers: dict,
        public_template: ProposalTemplate,
        test_user: User,
    ):
        response = await client.post(
            f"/api/v1/templates/{public_template.id}/rate",
            headers=auth_headers,
            json={"rating": 6},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_rate_private_template(
        self,
        client: AsyncClient,
        auth_headers: dict,
        user_template: ProposalTemplate,
        test_user: User,
    ):
        response = await client.post(
            f"/api/v1/templates/{user_template.id}/rate",
            headers=auth_headers,
            json={"rating": 3},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_rate_not_found(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.post(
            "/api/v1/templates/99999/rate",
            headers=auth_headers,
            json={"rating": 3},
        )
        assert response.status_code == 404
