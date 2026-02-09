"""
RFP Sniper - Template Library Tests
====================================
Tests for proposal template management.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestTemplateList:
    """Tests for template listing."""

    @pytest.mark.asyncio
    async def test_list_templates_empty(self, client: AsyncClient, auth_headers: dict):
        """Test listing templates when none exist."""
        response = await client.get(
            "/api/v1/templates/",
            headers=auth_headers,
        )
        assert response.status_code == 200
        # Returns empty list when no templates exist
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_list_templates_unauthorized(self, client: AsyncClient):
        """Test listing templates without auth."""
        response = await client.get("/api/v1/templates/")
        assert response.status_code == 401


class TestTemplateCreate:
    """Tests for template creation."""

    @pytest.mark.asyncio
    async def test_create_template_success(self, client: AsyncClient, auth_headers: dict):
        """Test creating a custom template."""
        response = await client.post(
            "/api/v1/templates/",
            headers=auth_headers,
            json={
                "name": "Custom Past Performance",
                "category": "Past Performance",
                "description": "A custom past performance template",
                "template_text": "**Project:** {project_name}\n**Value:** ${value}",
                "placeholders": {
                    "project_name": "Name of the project",
                    "value": "Contract value",
                },
                "keywords": ["past performance", "custom"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Custom Past Performance"
        assert data["is_system"] is False
        assert len(data["placeholders"]) == 2

    @pytest.mark.asyncio
    async def test_create_template_minimal(self, client: AsyncClient, auth_headers: dict):
        """Test creating template with minimal fields."""
        response = await client.post(
            "/api/v1/templates/",
            headers=auth_headers,
            json={
                "name": "Minimal Template",
                "category": "General",
                "description": "A minimal template",
                "template_text": "Simple text without placeholders",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Minimal Template"


class TestTemplateDetail:
    """Tests for template detail retrieval."""

    @pytest.mark.asyncio
    async def test_get_template_success(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Test getting a template by ID."""
        # First create a template
        from app.api.routes.templates import ProposalTemplate

        template = ProposalTemplate(
            name="Test Template",
            category="Test",
            description="Test description",
            template_text="Test content",
            is_system=True,
        )
        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)

        # Get the template
        response = await client.get(
            f"/api/v1/templates/{template.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Template"

    @pytest.mark.asyncio
    async def test_get_template_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test getting non-existent template."""
        response = await client.get(
            "/api/v1/templates/99999",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestTemplateUse:
    """Tests for using templates with placeholders."""

    @pytest.mark.asyncio
    async def test_use_template_success(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Test using a template with placeholder values."""
        from app.api.routes.templates import ProposalTemplate

        template = ProposalTemplate(
            name="Greeting Template",
            category="Test",
            description="A greeting template",
            template_text="Hello, {name}! Welcome to {company}.",
            placeholders={"name": "Person name", "company": "Company name"},
            is_system=True,
        )
        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)

        response = await client.post(
            f"/api/v1/templates/{template.id}/use",
            headers=auth_headers,
            json={"name": "John", "company": "Acme Inc"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["filled_text"] == "Hello, John! Welcome to Acme Inc."
        assert data["unfilled_placeholders"] == []

    @pytest.mark.asyncio
    async def test_use_template_partial_fill(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Test using template with some placeholders unfilled."""
        from app.api.routes.templates import ProposalTemplate

        template = ProposalTemplate(
            name="Partial Template",
            category="Test",
            description="Test template",
            template_text="Name: {name}, Date: {date}, Value: {value}",
            placeholders={
                "name": "Person name",
                "date": "Date",
                "value": "Value",
            },
            is_system=True,
        )
        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)

        response = await client.post(
            f"/api/v1/templates/{template.id}/use",
            headers=auth_headers,
            json={"name": "John"},  # Only fill one placeholder
        )
        assert response.status_code == 200
        data = response.json()
        assert "{date}" in data["filled_text"]
        assert "{value}" in data["filled_text"]
        assert "date" in data["unfilled_placeholders"]
        assert "value" in data["unfilled_placeholders"]


class TestTemplateCategories:
    """Tests for template categories."""

    @pytest.mark.asyncio
    async def test_list_categories(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Test listing template categories."""
        from app.api.routes.templates import ProposalTemplate

        # Create templates in different categories
        for category in ["Technical", "Past Performance", "Quality"]:
            template = ProposalTemplate(
                name=f"{category} Template",
                category=category,
                description="Test",
                template_text="Content",
                is_system=True,
            )
            db_session.add(template)
        await db_session.commit()

        response = await client.get(
            "/api/v1/templates/categories",
            headers=auth_headers,
        )
        assert response.status_code == 200
        categories = response.json()
        assert "Technical" in categories
        assert "Past Performance" in categories
        assert "Quality" in categories

    @pytest.mark.asyncio
    async def test_list_categories_legacy_alias(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Test legacy categories path still works for older clients."""
        from app.api.routes.templates import ProposalTemplate

        template = ProposalTemplate(
            name="Legacy Category Template",
            category="Legacy",
            description="Test",
            template_text="Content",
            is_system=True,
        )
        db_session.add(template)
        await db_session.commit()

        response = await client.get(
            "/api/v1/templates/categories/list",
            headers=auth_headers,
        )
        assert response.status_code == 200
        categories = response.json()
        assert "Legacy" in categories

    @pytest.mark.asyncio
    async def test_filter_by_category(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Test filtering templates by category."""
        from app.api.routes.templates import ProposalTemplate

        # Create templates
        tech_template = ProposalTemplate(
            name="Tech Template",
            category="Technical",
            description="Technical template",
            template_text="Content",
            is_system=True,
        )
        quality_template = ProposalTemplate(
            name="Quality Template",
            category="Quality",
            description="Quality template",
            template_text="Content",
            is_system=True,
        )
        db_session.add_all([tech_template, quality_template])
        await db_session.commit()

        response = await client.get(
            "/api/v1/templates/",
            headers=auth_headers,
            params={"category": "Technical"},
        )
        assert response.status_code == 200
        templates = response.json()
        assert all(t["category"] == "Technical" for t in templates)


class TestSeedTemplates:
    """Tests for seeding system templates."""

    @pytest.mark.asyncio
    async def test_seed_system_templates(self, client: AsyncClient):
        """Test seeding system templates."""
        response = await client.post("/api/v1/templates/seed-system-templates")
        assert response.status_code == 200
        data = response.json()
        assert "created" in data["message"].lower() or data["total_system_templates"] > 0

    @pytest.mark.asyncio
    async def test_seed_templates_idempotent(self, client: AsyncClient):
        """Test that seeding is idempotent."""
        # Seed once
        await client.post("/api/v1/templates/seed-system-templates")

        # Seed again
        response = await client.post("/api/v1/templates/seed-system-templates")
        assert response.status_code == 200
        # Second seed should create 0 new templates
        data = response.json()
        assert "0" in data["message"] or data["message"].startswith("Created 0")
