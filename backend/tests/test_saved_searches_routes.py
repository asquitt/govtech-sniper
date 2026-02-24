"""
Integration tests for saved_searches.py — /saved-searches/ CRUD and run
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.saved_search import SavedSearch
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password


async def _create_second_user(db_session: AsyncSession) -> tuple[User, dict]:
    user2 = User(
        email="other@example.com",
        hashed_password=hash_password("OtherPass123!"),
        full_name="Other User",
        company_name="Other Co",
        tier="professional",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user2)
    await db_session.commit()
    await db_session.refresh(user2)
    tokens = create_token_pair(user2.id, user2.email, user2.tier)
    return user2, {"Authorization": f"Bearer {tokens.access_token}"}


class TestListSavedSearches:
    """GET /api/v1/saved-searches"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/saved-searches")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_list(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.get("/api/v1/saved-searches", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []


class TestCreateSavedSearch:
    """POST /api/v1/saved-searches"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/saved-searches", json={"name": "Test", "filters": {}})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_search(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.post(
            "/api/v1/saved-searches",
            headers=auth_headers,
            json={
                "name": "Cyber RFPs",
                "filters": {"keywords": ["cybersecurity"], "agencies": ["DoD"]},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Cyber RFPs"
        assert data["is_active"] is True
        assert data["filters"]["keywords"] == ["cybersecurity"]


class TestUpdateSavedSearch:
    """PATCH /api/v1/saved-searches/{search_id}"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.patch("/api/v1/saved-searches/1", json={"name": "X"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_search(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        search = SavedSearch(user_id=test_user.id, name="Original", filters={})
        db_session.add(search)
        await db_session.commit()
        await db_session.refresh(search)

        response = await client.patch(
            f"/api/v1/saved-searches/{search.id}",
            headers=auth_headers,
            json={"name": "Updated Name", "is_active": False},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"
        assert response.json()["is_active"] is False

    @pytest.mark.asyncio
    async def test_update_not_found(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.patch(
            "/api/v1/saved-searches/99999", headers=auth_headers, json={"name": "X"}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_idor(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        user2, _ = await _create_second_user(db_session)
        search = SavedSearch(user_id=user2.id, name="Other's Search", filters={})
        db_session.add(search)
        await db_session.commit()
        await db_session.refresh(search)

        response = await client.patch(
            f"/api/v1/saved-searches/{search.id}",
            headers=auth_headers,
            json={"name": "Hacked"},
        )
        assert response.status_code == 404


class TestDeleteSavedSearch:
    """DELETE /api/v1/saved-searches/{search_id}"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.delete("/api/v1/saved-searches/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_search(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        search = SavedSearch(user_id=test_user.id, name="Delete Me", filters={})
        db_session.add(search)
        await db_session.commit()
        await db_session.refresh(search)

        response = await client.delete(f"/api/v1/saved-searches/{search.id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["message"] == "Saved search deleted"

    @pytest.mark.asyncio
    async def test_delete_not_found(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.delete("/api/v1/saved-searches/99999", headers=auth_headers)
        assert response.status_code == 404


class TestRunSavedSearch:
    """POST /api/v1/saved-searches/{search_id}/run"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/saved-searches/1/run")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_run_search(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        search = SavedSearch(
            user_id=test_user.id,
            name="Run Me",
            filters={"keywords": ["cybersecurity"]},
        )
        db_session.add(search)
        await db_session.commit()
        await db_session.refresh(search)

        response = await client.post(
            f"/api/v1/saved-searches/{search.id}/run", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["search_id"] == search.id
        assert "match_count" in data
        assert "matches" in data
        assert "ran_at" in data

    @pytest.mark.asyncio
    async def test_run_not_found(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.post("/api/v1/saved-searches/99999/run", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_run_updates_metadata(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        search = SavedSearch(user_id=test_user.id, name="Track Run", filters={})
        db_session.add(search)
        await db_session.commit()
        await db_session.refresh(search)
        assert search.last_run_at is None

        await client.post(f"/api/v1/saved-searches/{search.id}/run", headers=auth_headers)

        # Verify the search was updated by listing
        list_response = await client.get("/api/v1/saved-searches", headers=auth_headers)
        updated = [s for s in list_response.json() if s["id"] == search.id][0]
        assert updated["last_run_at"] is not None
