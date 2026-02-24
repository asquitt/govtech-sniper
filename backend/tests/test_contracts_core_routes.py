"""
Integration tests for contracts/core.py:
  - GET    /contracts/
  - POST   /contracts/
  - GET    /contracts/{contract_id}
  - PATCH  /contracts/{contract_id}
  - DELETE /contracts/{contract_id}
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contract import ContractAward
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password

BASE = "/api/v1/contracts"


@pytest_asyncio.fixture
async def test_contract(db_session: AsyncSession, test_user: User) -> ContractAward:
    """Create a test contract for the test user."""
    contract = ContractAward(
        user_id=test_user.id,
        contract_number="W912HV-24-C-0001",
        title="Test Cybersecurity Services Contract",
        agency="Department of Defense",
        contract_type="prime",
        status="active",
        value=2500000.0,
        classification="internal",
    )
    db_session.add(contract)
    await db_session.commit()
    await db_session.refresh(contract)
    return contract


class TestListContracts:
    """Tests for GET /contracts/."""

    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client: AsyncClient):
        response = await client.get(BASE)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_empty(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(BASE, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["contracts"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_returns_user_contracts(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
    ):
        response = await client.get(BASE, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["contracts"][0]["id"] == test_contract.id
        assert data["contracts"][0]["contract_number"] == "W912HV-24-C-0001"

    @pytest.mark.asyncio
    async def test_list_idor_isolation(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_contract: ContractAward,
    ):
        """Second user should not see first user's contracts."""
        other_user = User(
            email="other@example.com",
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

        response = await client.get(BASE, headers=headers)
        assert response.status_code == 200
        assert response.json()["total"] == 0


class TestCreateContract:
    """Tests for POST /contracts/."""

    @pytest.mark.asyncio
    async def test_create_requires_auth(self, client: AsyncClient):
        response = await client.post(BASE, json={"contract_number": "X", "title": "Y"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_minimal(self, client: AsyncClient, auth_headers: dict):
        payload = {"contract_number": "GS-35F-0001", "title": "IT Services BPA"}
        response = await client.post(BASE, json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["contract_number"] == "GS-35F-0001"
        assert data["title"] == "IT Services BPA"
        assert data["status"] == "active"
        assert data["classification"] == "internal"

    @pytest.mark.asyncio
    async def test_create_full_payload(self, client: AsyncClient, auth_headers: dict):
        payload = {
            "contract_number": "FA8750-24-C-0100",
            "title": "AI Research Contract",
            "agency": "Air Force Research Lab",
            "contract_type": "prime",
            "start_date": "2024-01-01",
            "end_date": "2025-12-31",
            "value": 5000000.0,
            "status": "active",
            "classification": "fci",
            "summary": "Advanced AI research.",
        }
        response = await client.post(BASE, json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["agency"] == "Air Force Research Lab"
        assert data["value"] == 5000000.0
        assert data["classification"] == "fci"

    @pytest.mark.asyncio
    async def test_create_with_parent_contract(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
    ):
        payload = {
            "contract_number": "TO-001",
            "title": "Task Order under IDIQ",
            "parent_contract_id": test_contract.id,
            "contract_type": "task_order",
        }
        response = await client.post(BASE, json=payload, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["parent_contract_id"] == test_contract.id

    @pytest.mark.asyncio
    async def test_create_with_invalid_parent(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        payload = {
            "contract_number": "TO-BAD",
            "title": "Bad Parent",
            "parent_contract_id": 99999,
        }
        response = await client.post(BASE, json=payload, headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_missing_required_fields(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(BASE, json={}, headers=auth_headers)
        assert response.status_code == 422


class TestGetContract:
    """Tests for GET /contracts/{contract_id}."""

    @pytest.mark.asyncio
    async def test_get_requires_auth(self, client: AsyncClient):
        response = await client.get(f"{BASE}/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
    ):
        response = await client.get(f"{BASE}/{test_contract.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_contract.id
        assert data["title"] == test_contract.title

    @pytest.mark.asyncio
    async def test_get_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(f"{BASE}/99999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_contract: ContractAward,
    ):
        """Another user cannot access this contract."""
        other_user = User(
            email="idor@example.com",
            hashed_password=hash_password("IdorPass123!"),
            full_name="IDOR User",
            company_name="IDOR Co",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(other_user)

        tokens = create_token_pair(other_user.id, other_user.email, other_user.tier)
        headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.get(f"{BASE}/{test_contract.id}", headers=headers)
        assert response.status_code == 404


class TestUpdateContract:
    """Tests for PATCH /contracts/{contract_id}."""

    @pytest.mark.asyncio
    async def test_update_requires_auth(self, client: AsyncClient):
        response = await client.patch(f"{BASE}/1", json={"title": "X"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
    ):
        payload = {"title": "Updated Title", "value": 3000000.0}
        response = await client.patch(
            f"{BASE}/{test_contract.id}", json=payload, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["value"] == 3000000.0

    @pytest.mark.asyncio
    async def test_update_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.patch(f"{BASE}/99999", json={"title": "X"}, headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_contract: ContractAward,
    ):
        other_user = User(
            email="idor2@example.com",
            hashed_password=hash_password("IdorPass123!"),
            full_name="IDOR2 User",
            company_name="IDOR2 Co",
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
            f"{BASE}/{test_contract.id}",
            json={"title": "Hacked"},
            headers=headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_self_parent_rejected(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
    ):
        """Contract cannot be its own parent."""
        response = await client.patch(
            f"{BASE}/{test_contract.id}",
            json={"parent_contract_id": test_contract.id},
            headers=auth_headers,
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_update_circular_parent_rejected(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Circular parent chain is rejected."""
        c1 = ContractAward(
            user_id=test_user.id,
            contract_number="C1",
            title="Contract 1",
        )
        db_session.add(c1)
        await db_session.flush()

        c2 = ContractAward(
            user_id=test_user.id,
            contract_number="C2",
            title="Contract 2",
            parent_contract_id=c1.id,
        )
        db_session.add(c2)
        await db_session.commit()
        await db_session.refresh(c1)
        await db_session.refresh(c2)

        # Try to make C1's parent = C2 (circular)
        response = await client.patch(
            f"{BASE}/{c1.id}",
            json={"parent_contract_id": c2.id},
            headers=auth_headers,
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_update_invalid_parent_rejected(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
    ):
        """Non-existent parent contract is rejected."""
        response = await client.patch(
            f"{BASE}/{test_contract.id}",
            json={"parent_contract_id": 99999},
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestDeleteContract:
    """Tests for DELETE /contracts/{contract_id}."""

    @pytest.mark.asyncio
    async def test_delete_requires_auth(self, client: AsyncClient):
        response = await client.delete(f"{BASE}/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
    ):
        response = await client.delete(f"{BASE}/{test_contract.id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["message"] == "Contract deleted"

        # Verify deleted
        response = await client.get(f"{BASE}/{test_contract.id}", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.delete(f"{BASE}/99999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_contract: ContractAward,
    ):
        other_user = User(
            email="idor3@example.com",
            hashed_password=hash_password("IdorPass123!"),
            full_name="IDOR3 User",
            company_name="IDOR3 Co",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(other_user)

        tokens = create_token_pair(other_user.id, other_user.email, other_user.tier)
        headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.delete(f"{BASE}/{test_contract.id}", headers=headers)
        assert response.status_code == 404
