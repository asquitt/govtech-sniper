"""
Integration tests for contacts.py — /contacts/ CRUD, search, agencies
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import OpportunityContact
from app.models.rfp import RFP
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
    headers = {"Authorization": f"Bearer {tokens.access_token}"}
    return user2, headers


class TestListContacts:
    """GET /api/v1/contacts"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/contacts")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_list(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.get("/api/v1/contacts", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_returns_own_contacts(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        contact = OpportunityContact(
            user_id=test_user.id, name="Jane Doe", email="jane@example.com"
        )
        db_session.add(contact)
        await db_session.commit()

        response = await client.get("/api/v1/contacts", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Jane Doe"

    @pytest.mark.asyncio
    async def test_idor_contacts_not_visible(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        user2, _ = await _create_second_user(db_session)
        contact = OpportunityContact(
            user_id=user2.id, name="Secret Contact", email="secret@example.com"
        )
        db_session.add(contact)
        await db_session.commit()

        response = await client.get("/api/v1/contacts", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 0


class TestCreateContact:
    """POST /api/v1/contacts"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/contacts", json={"name": "Test"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_contact(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.post(
            "/api/v1/contacts",
            headers=auth_headers,
            json={"name": "John Smith", "email": "john@example.com", "role": "CO"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "John Smith"
        assert data["email"] == "john@example.com"
        assert data["role"] == "CO"

    @pytest.mark.asyncio
    async def test_create_contact_with_rfp(
        self, client: AsyncClient, auth_headers: dict, test_user: User, test_rfp: RFP
    ):
        response = await client.post(
            "/api/v1/contacts",
            headers=auth_headers,
            json={"name": "Jane Doe", "rfp_id": test_rfp.id},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["rfp_id"] == test_rfp.id

    @pytest.mark.asyncio
    async def test_create_contact_rfp_not_found(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.post(
            "/api/v1/contacts",
            headers=auth_headers,
            json={"name": "Jane Doe", "rfp_id": 99999},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_deduplication_by_email(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        payload = {"name": "Same Person", "email": "dupe@example.com"}
        r1 = await client.post("/api/v1/contacts", headers=auth_headers, json=payload)
        assert r1.status_code == 200
        id1 = r1.json()["id"]

        r2 = await client.post("/api/v1/contacts", headers=auth_headers, json=payload)
        assert r2.status_code == 200
        # Should link existing rather than create new
        assert r2.json()["id"] == id1


class TestUpdateContact:
    """PATCH /api/v1/contacts/{contact_id}"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.patch("/api/v1/contacts/1", json={"name": "New"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_contact(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        contact = OpportunityContact(user_id=test_user.id, name="Original")
        db_session.add(contact)
        await db_session.commit()
        await db_session.refresh(contact)

        response = await client.patch(
            f"/api/v1/contacts/{contact.id}",
            headers=auth_headers,
            json={"name": "Updated", "role": "COR"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated"
        assert response.json()["role"] == "COR"

    @pytest.mark.asyncio
    async def test_update_not_found(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.patch(
            "/api/v1/contacts/99999", headers=auth_headers, json={"name": "X"}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_idor(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        user2, _ = await _create_second_user(db_session)
        contact = OpportunityContact(user_id=user2.id, name="Other's Contact")
        db_session.add(contact)
        await db_session.commit()
        await db_session.refresh(contact)

        response = await client.patch(
            f"/api/v1/contacts/{contact.id}", headers=auth_headers, json={"name": "Hacked"}
        )
        assert response.status_code == 404


class TestDeleteContact:
    """DELETE /api/v1/contacts/{contact_id}"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.delete("/api/v1/contacts/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_contact(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        contact = OpportunityContact(user_id=test_user.id, name="Delete Me")
        db_session.add(contact)
        await db_session.commit()
        await db_session.refresh(contact)

        response = await client.delete(f"/api/v1/contacts/{contact.id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["message"] == "Contact deleted"

    @pytest.mark.asyncio
    async def test_delete_not_found(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.delete("/api/v1/contacts/99999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_idor(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        user2, _ = await _create_second_user(db_session)
        contact = OpportunityContact(user_id=user2.id, name="Not Yours")
        db_session.add(contact)
        await db_session.commit()
        await db_session.refresh(contact)

        response = await client.delete(f"/api/v1/contacts/{contact.id}", headers=auth_headers)
        assert response.status_code == 404


class TestSearchContacts:
    """GET /api/v1/contacts/search"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/contacts/search")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_search_by_name(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        db_session.add(OpportunityContact(user_id=test_user.id, name="Alice Smith", agency="DoD"))
        db_session.add(OpportunityContact(user_id=test_user.id, name="Bob Jones", agency="GSA"))
        await db_session.commit()

        response = await client.get(
            "/api/v1/contacts/search", headers=auth_headers, params={"name": "Alice"}
        )
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["name"] == "Alice Smith"

    @pytest.mark.asyncio
    async def test_search_by_agency(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        db_session.add(OpportunityContact(user_id=test_user.id, name="Alice", agency="DoD"))
        db_session.add(OpportunityContact(user_id=test_user.id, name="Bob", agency="GSA"))
        await db_session.commit()

        response = await client.get(
            "/api/v1/contacts/search", headers=auth_headers, params={"agency": "DoD"}
        )
        assert response.status_code == 200
        assert len(response.json()) == 1


class TestAgencies:
    """GET/POST /api/v1/contacts/agencies"""

    @pytest.mark.asyncio
    async def test_list_agencies_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/contacts/agencies")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_and_list_agency(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.post(
            "/api/v1/contacts/agencies",
            headers=auth_headers,
            json={"agency_name": "Department of Defense", "website": "https://dod.gov"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["agency_name"] == "Department of Defense"

        list_response = await client.get("/api/v1/contacts/agencies", headers=auth_headers)
        assert list_response.status_code == 200
        assert len(list_response.json()) == 1

    @pytest.mark.asyncio
    async def test_upsert_agency(self, client: AsyncClient, auth_headers: dict, test_user: User):
        payload = {"agency_name": "GSA", "website": "https://gsa.gov"}
        r1 = await client.post("/api/v1/contacts/agencies", headers=auth_headers, json=payload)
        assert r1.status_code == 200

        payload["website"] = "https://www.gsa.gov"
        r2 = await client.post("/api/v1/contacts/agencies", headers=auth_headers, json=payload)
        assert r2.status_code == 200
        assert r2.json()["id"] == r1.json()["id"]
        assert r2.json()["website"] == "https://www.gsa.gov"
