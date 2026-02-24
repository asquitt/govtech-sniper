"""
Integration tests for support.py — /support/ help articles, tutorials, chat
"""

import pytest
from httpx import AsyncClient

from app.models.user import User


class TestListHelpArticles:
    """GET /api/v1/support/help-center/articles"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/support/help-center/articles")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_all_articles(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.get("/api/v1/support/help-center/articles", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 4
        assert all("id" in a and "title" in a for a in data)

    @pytest.mark.asyncio
    async def test_filter_by_category(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.get(
            "/api/v1/support/help-center/articles",
            headers=auth_headers,
            params={"category": "Onboarding"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert all(a["category"] == "Onboarding" for a in data)

    @pytest.mark.asyncio
    async def test_search_articles(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.get(
            "/api/v1/support/help-center/articles",
            headers=auth_headers,
            params={"q": "template"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_search_no_results(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.get(
            "/api/v1/support/help-center/articles",
            headers=auth_headers,
            params={"q": "xyznonexistent"},
        )
        assert response.status_code == 200
        assert response.json() == []


class TestGetHelpArticle:
    """GET /api/v1/support/help-center/articles/{article_id}"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get(
            "/api/v1/support/help-center/articles/getting-started-first-proposal"
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_article(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.get(
            "/api/v1/support/help-center/articles/getting-started-first-proposal",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "getting-started-first-proposal"
        assert "title" in data

    @pytest.mark.asyncio
    async def test_article_not_found(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.get(
            "/api/v1/support/help-center/articles/nonexistent-article",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestListTutorials:
    """GET /api/v1/support/tutorials"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/support/tutorials")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_all_tutorials(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.get("/api/v1/support/tutorials", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3
        assert all("steps" in t for t in data)

    @pytest.mark.asyncio
    async def test_filter_by_feature(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.get(
            "/api/v1/support/tutorials",
            headers=auth_headers,
            params={"feature": "Onboarding"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert all(t["feature"] == "Onboarding" for t in data)


class TestGetTutorial:
    """GET /api/v1/support/tutorials/{tutorial_id}"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/support/tutorials/tutorial-first-proposal")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_tutorial(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.get(
            "/api/v1/support/tutorials/tutorial-first-proposal", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "tutorial-first-proposal"
        assert len(data["steps"]) >= 1

    @pytest.mark.asyncio
    async def test_tutorial_not_found(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.get(
            "/api/v1/support/tutorials/nonexistent-tutorial", headers=auth_headers
        )
        assert response.status_code == 404


class TestSupportChat:
    """POST /api/v1/support/chat"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/support/chat", json={"message": "help"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_chat_template_query(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.post(
            "/api/v1/support/chat",
            headers=auth_headers,
            json={"message": "How do I use templates?"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
        assert "template-marketplace-playbook" in data["suggested_article_ids"]
        assert data["suggested_tutorial_id"] == "tutorial-template-marketplace"

    @pytest.mark.asyncio
    async def test_chat_onboarding_query(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.post(
            "/api/v1/support/chat",
            headers=auth_headers,
            json={"message": "How do I start my first proposal?"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "getting-started-first-proposal" in data["suggested_article_ids"]

    @pytest.mark.asyncio
    async def test_chat_report_query(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.post(
            "/api/v1/support/chat",
            headers=auth_headers,
            json={"message": "How do I create a report?"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "report-builder-guide" in data["suggested_article_ids"]

    @pytest.mark.asyncio
    async def test_chat_with_route_context(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.post(
            "/api/v1/support/chat",
            headers=auth_headers,
            json={"message": "help me", "current_route": "/reports"},
        )
        assert response.status_code == 200
        assert response.json()["suggested_tutorial_id"] == "tutorial-reports"

    @pytest.mark.asyncio
    async def test_chat_generic_query(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.post(
            "/api/v1/support/chat",
            headers=auth_headers,
            json={"message": "I need help with something random"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
        assert "generated_at" in data
