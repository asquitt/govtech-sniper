"""
Integration tests for contracts/clins.py:
  - GET    /contracts/{contract_id}/clins
  - POST   /contracts/{contract_id}/clins
  - PATCH  /contracts/{contract_id}/clins/{clin_id}
  - DELETE /contracts/{contract_id}/clins/{clin_id}
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contract import ContractAward, ContractCLIN
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password

BASE = "/api/v1/contracts"


@pytest_asyncio.fixture
async def test_contract(db_session: AsyncSession, test_user: User) -> ContractAward:
    contract = ContractAward(
        user_id=test_user.id,
        contract_number="W912HV-24-C-0004",
        title="CLINs Test Contract",
    )
    db_session.add(contract)
    await db_session.commit()
    await db_session.refresh(contract)
    return contract


@pytest_asyncio.fixture
async def test_clin(db_session: AsyncSession, test_contract: ContractAward) -> ContractCLIN:
    clin = ContractCLIN(
        contract_id=test_contract.id,
        clin_number="0001",
        description="Base engineering services",
        clin_type="ffp",
        unit_price=150.0,
        quantity=1000,
        total_value=150000.0,
        funded_amount=75000.0,
    )
    db_session.add(clin)
    await db_session.commit()
    await db_session.refresh(clin)
    return clin


class TestListCLINs:
    """Tests for GET /contracts/{contract_id}/clins."""

    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client: AsyncClient):
        response = await client.get(f"{BASE}/1/clins")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_empty(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
    ):
        response = await client.get(f"{BASE}/{test_contract.id}/clins", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_returns_clins(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
        test_clin: ContractCLIN,
    ):
        response = await client.get(f"{BASE}/{test_contract.id}/clins", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["clin_number"] == "0001"
        assert data[0]["total_value"] == 150000.0

    @pytest.mark.asyncio
    async def test_list_contract_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(f"{BASE}/99999/clins", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_contract: ContractAward,
    ):
        other_user = User(
            email="other_clin@example.com",
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

        response = await client.get(f"{BASE}/{test_contract.id}/clins", headers=headers)
        assert response.status_code == 404


class TestCreateCLIN:
    """Tests for POST /contracts/{contract_id}/clins."""

    @pytest.mark.asyncio
    async def test_create_requires_auth(self, client: AsyncClient):
        response = await client.post(f"{BASE}/1/clins", json={"clin_number": "0001"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
    ):
        payload = {
            "clin_number": "0002",
            "description": "Travel expenses",
            "clin_type": "t_and_m",
            "unit_price": 200.0,
            "quantity": 50,
            "total_value": 10000.0,
            "funded_amount": 5000.0,
        }
        response = await client.post(
            f"{BASE}/{test_contract.id}/clins",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["clin_number"] == "0002"
        assert data["contract_id"] == test_contract.id
        assert data["clin_type"] == "t_and_m"

    @pytest.mark.asyncio
    async def test_create_minimal(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
    ):
        payload = {"clin_number": "0003"}
        response = await client.post(
            f"{BASE}/{test_contract.id}/clins",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_create_contract_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            f"{BASE}/99999/clins",
            json={"clin_number": "X"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_missing_clin_number(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
    ):
        response = await client.post(
            f"{BASE}/{test_contract.id}/clins",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestUpdateCLIN:
    """Tests for PATCH /contracts/{contract_id}/clins/{clin_id}."""

    @pytest.mark.asyncio
    async def test_update_requires_auth(self, client: AsyncClient):
        response = await client.patch(f"{BASE}/1/clins/1", json={"description": "X"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
        test_clin: ContractCLIN,
    ):
        payload = {"description": "Updated services", "funded_amount": 100000.0}
        response = await client.patch(
            f"{BASE}/{test_contract.id}/clins/{test_clin.id}",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated services"
        assert data["funded_amount"] == 100000.0

    @pytest.mark.asyncio
    async def test_update_contract_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.patch(
            f"{BASE}/99999/clins/1",
            json={"description": "X"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_clin_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
    ):
        response = await client.patch(
            f"{BASE}/{test_contract.id}/clins/99999",
            json={"description": "X"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_contract: ContractAward,
        test_clin: ContractCLIN,
    ):
        other_user = User(
            email="idor_clin@example.com",
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
            f"{BASE}/{test_contract.id}/clins/{test_clin.id}",
            json={"description": "Hacked"},
            headers=headers,
        )
        assert response.status_code == 404


class TestDeleteCLIN:
    """Tests for DELETE /contracts/{contract_id}/clins/{clin_id}."""

    @pytest.mark.asyncio
    async def test_delete_requires_auth(self, client: AsyncClient):
        response = await client.delete(f"{BASE}/1/clins/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
        test_clin: ContractCLIN,
    ):
        response = await client.delete(
            f"{BASE}/{test_contract.id}/clins/{test_clin.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["message"] == "CLIN deleted"

    @pytest.mark.asyncio
    async def test_delete_contract_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.delete(f"{BASE}/99999/clins/1", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_clin_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
    ):
        response = await client.delete(
            f"{BASE}/{test_contract.id}/clins/99999",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_contract: ContractAward,
        test_clin: ContractCLIN,
    ):
        other_user = User(
            email="idor_clin2@example.com",
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
            f"{BASE}/{test_contract.id}/clins/{test_clin.id}",
            headers=headers,
        )
        assert response.status_code == 404
