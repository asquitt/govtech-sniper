"""
Integration tests for contracts/deliverables.py:
  - GET    /contracts/{contract_id}/deliverables
  - POST   /contracts/{contract_id}/deliverables
  - PATCH  /contracts/deliverables/{deliverable_id}
  - DELETE /contracts/deliverables/{deliverable_id}
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contract import ContractAward, ContractDeliverable
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password

BASE = "/api/v1/contracts"


@pytest_asyncio.fixture
async def test_contract(db_session: AsyncSession, test_user: User) -> ContractAward:
    contract = ContractAward(
        user_id=test_user.id,
        contract_number="W912HV-24-C-0002",
        title="Deliverables Test Contract",
    )
    db_session.add(contract)
    await db_session.commit()
    await db_session.refresh(contract)
    return contract


@pytest_asyncio.fixture
async def test_deliverable(
    db_session: AsyncSession, test_contract: ContractAward
) -> ContractDeliverable:
    deliverable = ContractDeliverable(
        contract_id=test_contract.id,
        title="Monthly Progress Report",
        status="pending",
        notes="Due every 15th.",
    )
    db_session.add(deliverable)
    await db_session.commit()
    await db_session.refresh(deliverable)
    return deliverable


class TestListDeliverables:
    """Tests for GET /contracts/{contract_id}/deliverables."""

    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client: AsyncClient):
        response = await client.get(f"{BASE}/1/deliverables")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_empty(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
    ):
        response = await client.get(f"{BASE}/{test_contract.id}/deliverables", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_returns_deliverables(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
        test_deliverable: ContractDeliverable,
    ):
        response = await client.get(f"{BASE}/{test_contract.id}/deliverables", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Monthly Progress Report"

    @pytest.mark.asyncio
    async def test_list_contract_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(f"{BASE}/99999/deliverables", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_contract: ContractAward,
    ):
        other_user = User(
            email="other_deliv@example.com",
            hashed_password=hash_password("OtherPass123!"),
            full_name="Other User",
            company_name="Other Co",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(other_user)

        tokens = create_token_pair(other_user.id, other_user.email, other_user.tier)
        headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.get(f"{BASE}/{test_contract.id}/deliverables", headers=headers)
        assert response.status_code == 404


class TestCreateDeliverable:
    """Tests for POST /contracts/{contract_id}/deliverables."""

    @pytest.mark.asyncio
    async def test_create_requires_auth(self, client: AsyncClient):
        response = await client.post(f"{BASE}/1/deliverables", json={"title": "X"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
    ):
        payload = {
            "title": "Security Assessment Report",
            "due_date": "2025-06-15",
            "status": "pending",
            "notes": "Quarterly deliverable",
        }
        response = await client.post(
            f"{BASE}/{test_contract.id}/deliverables",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Security Assessment Report"
        assert data["contract_id"] == test_contract.id
        assert data["notes"] == "Quarterly deliverable"

    @pytest.mark.asyncio
    async def test_create_minimal(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
    ):
        payload = {"title": "Minimal Deliverable"}
        response = await client.post(
            f"{BASE}/{test_contract.id}/deliverables",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "pending"

    @pytest.mark.asyncio
    async def test_create_contract_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            f"{BASE}/99999/deliverables",
            json={"title": "Orphan"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_missing_title(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
    ):
        response = await client.post(
            f"{BASE}/{test_contract.id}/deliverables",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestUpdateDeliverable:
    """Tests for PATCH /contracts/deliverables/{deliverable_id}."""

    @pytest.mark.asyncio
    async def test_update_requires_auth(self, client: AsyncClient):
        response = await client.patch(f"{BASE}/deliverables/1", json={"title": "X"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_deliverable: ContractDeliverable,
    ):
        payload = {"title": "Updated Report", "status": "in_progress"}
        response = await client.patch(
            f"{BASE}/deliverables/{test_deliverable.id}",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Report"
        assert data["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_update_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.patch(
            f"{BASE}/deliverables/99999",
            json={"title": "X"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_deliverable: ContractDeliverable,
    ):
        other_user = User(
            email="idor_deliv@example.com",
            hashed_password=hash_password("OtherPass123!"),
            full_name="Other User",
            company_name="Other Co",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(other_user)

        tokens = create_token_pair(other_user.id, other_user.email, other_user.tier)
        headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.patch(
            f"{BASE}/deliverables/{test_deliverable.id}",
            json={"title": "Hacked"},
            headers=headers,
        )
        assert response.status_code == 404


class TestDeleteDeliverable:
    """Tests for DELETE /contracts/deliverables/{deliverable_id}."""

    @pytest.mark.asyncio
    async def test_delete_requires_auth(self, client: AsyncClient):
        response = await client.delete(f"{BASE}/deliverables/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_deliverable: ContractDeliverable,
    ):
        response = await client.delete(
            f"{BASE}/deliverables/{test_deliverable.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Deliverable deleted"

    @pytest.mark.asyncio
    async def test_delete_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.delete(f"{BASE}/deliverables/99999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_deliverable: ContractDeliverable,
    ):
        other_user = User(
            email="idor_deliv2@example.com",
            hashed_password=hash_password("OtherPass123!"),
            full_name="Other User",
            company_name="Other Co",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(other_user)

        tokens = create_token_pair(other_user.id, other_user.email, other_user.tier)
        headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.delete(
            f"{BASE}/deliverables/{test_deliverable.id}",
            headers=headers,
        )
        assert response.status_code == 404
