"""
Integration tests for templates/crud.py:
  - GET  /templates/
  - GET  /templates/categories
  - GET  /templates/{id}
  - POST /templates/
  - POST /templates/{id}/use
  - POST /templates/seed-system-templates
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.templates.models import ProposalTemplate
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password


@pytest.fixture
async def test_template(db_session: AsyncSession, test_user: User) -> ProposalTemplate:
    """Create a user-owned template for testing."""
    t = ProposalTemplate(
        name="Past Performance Narrative",
        category="Past Performance",
        description="A template for describing past performance.",
        template_text="On project {project_name}, {company_name} delivered...",
        placeholders={"project_name": "Project Name", "company_name": "Company Name"},
        keywords=["past performance", "narrative"],
        is_system=False,
        user_id=test_user.id,
    )
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    return t


class TestListTemplates:
    """Tests for GET /api/v1/templates/."""

    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/templates/")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_templates_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_template: ProposalTemplate,
        test_user: User,
    ):
        response = await client.get("/api/v1/templates/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should include system templates + user template
        names = [t["name"] for t in data]
        assert "Past Performance Narrative" in names

    @pytest.mark.asyncio
    async def test_list_templates_filter_category(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_template: ProposalTemplate,
        test_user: User,
    ):
        response = await client.get(
            "/api/v1/templates/?category=Past Performance",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert all(t["category"] == "Past Performance" for t in data)

    @pytest.mark.asyncio
    async def test_list_templates_search(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_template: ProposalTemplate,
        test_user: User,
    ):
        response = await client.get(
            "/api/v1/templates/?search=narrative",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert any("Narrative" in t["name"] for t in data)


class TestGetTemplate:
    """Tests for GET /api/v1/templates/{id}."""

    @pytest.mark.asyncio
    async def test_get_template_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/templates/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_template_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_template: ProposalTemplate,
        test_user: User,
    ):
        response = await client.get(f"/api/v1/templates/{test_template.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Past Performance Narrative"

    @pytest.mark.asyncio
    async def test_get_template_not_found(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.get("/api/v1/templates/99999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_template_idor(
        self,
        client: AsyncClient,
        test_template: ProposalTemplate,
        db_session: AsyncSession,
    ):
        """Non-system template owned by user A is inaccessible to user B."""
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

        response = await client.get(f"/api/v1/templates/{test_template.id}", headers=headers)
        assert response.status_code == 403


class TestCreateTemplate:
    """Tests for POST /api/v1/templates/."""

    @pytest.mark.asyncio
    async def test_create_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/templates/",
            json={
                "name": "Test",
                "category": "General",
                "description": "Desc",
                "template_text": "Text",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_template_success(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.post(
            "/api/v1/templates/",
            headers=auth_headers,
            json={
                "name": "Custom Template",
                "category": "Technical",
                "description": "Custom description",
                "template_text": "Template body {var}",
                "placeholders": {"var": "Placeholder"},
                "keywords": ["custom"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Custom Template"
        assert data["is_system"] is False
        assert data["user_id"] == test_user.id


class TestUseTemplate:
    """Tests for POST /api/v1/templates/{id}/use."""

    @pytest.mark.asyncio
    async def test_use_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/templates/1/use",
            json={"project_name": "Test"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_use_template_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_template: ProposalTemplate,
        test_user: User,
    ):
        response = await client.post(
            f"/api/v1/templates/{test_template.id}/use",
            headers=auth_headers,
            json={"project_name": "Alpha", "company_name": "Acme"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "Alpha" in data["filled_text"]
        assert "Acme" in data["filled_text"]
        assert data["unfilled_placeholders"] == []

    @pytest.mark.asyncio
    async def test_use_template_unfilled_placeholders(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_template: ProposalTemplate,
        test_user: User,
    ):
        response = await client.post(
            f"/api/v1/templates/{test_template.id}/use",
            headers=auth_headers,
            json={"project_name": "Alpha"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "company_name" in data["unfilled_placeholders"]

    @pytest.mark.asyncio
    async def test_use_template_not_found(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.post(
            "/api/v1/templates/99999/use",
            headers=auth_headers,
            json={},
        )
        assert response.status_code == 404


class TestSeedSystemTemplates:
    """Tests for POST /api/v1/templates/seed-system-templates."""

    @pytest.mark.asyncio
    async def test_seed_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/templates/seed-system-templates")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_seed_success(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.post(
            "/api/v1/templates/seed-system-templates", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "total_system_templates" in data


class TestListCategories:
    """Tests for GET /api/v1/templates/categories."""

    @pytest.mark.asyncio
    async def test_categories_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/templates/categories")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_categories_success(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.get("/api/v1/templates/categories", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
