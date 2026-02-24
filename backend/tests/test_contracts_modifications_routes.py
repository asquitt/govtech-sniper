"""
Integration tests for contracts/modifications.py:
  - GET    /contracts/{contract_id}/modifications
  - POST   /contracts/{contract_id}/modifications
  - DELETE /contracts/{contract_id}/modifications/{mod_id}
"""

from datetime import date

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contract import ContractAward, ContractModification
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password

BASE = "/api/v1/contracts"


@pytest_asyncio.fixture
async def test_contract(db_session: AsyncSession, test_user: User) -> ContractAward:
    contract = ContractAward(
        user_id=test_user.id,
        contract_number="W912HV-24-C-0007",
        title="Modifications Test Contract",
    )
    db_session.add(contract)
    await db_session.commit()
    await db_session.refresh(contract)
    return contract


@pytest_asyncio.fixture
async def test_modification(
    db_session: AsyncSession, test_contract: ContractAward
) -> ContractModification:
    mod = ContractModification(
        contract_id=test_contract.id,
        modification_number="P00001",
        mod_type="funding",
        description="Incremental funding for option year 1.",
        effective_date=date(2024, 6, 1),
        value_change=500000.0,
    )
    db_session.add(mod)
    await db_session.commit()
    await db_session.refresh(mod)
    return mod


class TestListModifications:
    """Tests for GET /contracts/{contract_id}/modifications."""

    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client: AsyncClient):
        response = await client.get(f"{BASE}/1/modifications")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_empty(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
    ):
        response = await client.get(
            f"{BASE}/{test_contract.id}/modifications", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_returns_modifications(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
        test_modification: ContractModification,
    ):
        response = await client.get(
            f"{BASE}/{test_contract.id}/modifications", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["modification_number"] == "P00001"
        assert data[0]["value_change"] == 500000.0

    @pytest.mark.asyncio
    async def test_list_contract_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(f"{BASE}/99999/modifications", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_contract: ContractAward,
    ):
        other_user = User(
            email="other_mod@example.com",
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

        response = await client.get(f"{BASE}/{test_contract.id}/modifications", headers=headers)
        assert response.status_code == 404


class TestCreateModification:
    """Tests for POST /contracts/{contract_id}/modifications."""

    @pytest.mark.asyncio
    async def test_create_requires_auth(self, client: AsyncClient):
        response = await client.post(
            f"{BASE}/1/modifications",
            json={"modification_number": "P00001"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
    ):
        payload = {
            "modification_number": "P00002",
            "mod_type": "scope",
            "description": "Added cybersecurity assessment task.",
            "effective_date": "2024-09-01",
            "value_change": 200000.0,
        }
        response = await client.post(
            f"{BASE}/{test_contract.id}/modifications",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["modification_number"] == "P00002"
        assert data["contract_id"] == test_contract.id
        assert data["mod_type"] == "scope"

    @pytest.mark.asyncio
    async def test_create_minimal(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
    ):
        payload = {"modification_number": "A00001"}
        response = await client.post(
            f"{BASE}/{test_contract.id}/modifications",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_create_contract_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            f"{BASE}/99999/modifications",
            json={"modification_number": "X"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_missing_mod_number(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
    ):
        response = await client.post(
            f"{BASE}/{test_contract.id}/modifications",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestDeleteModification:
    """Tests for DELETE /contracts/{contract_id}/modifications/{mod_id}."""

    @pytest.mark.asyncio
    async def test_delete_requires_auth(self, client: AsyncClient):
        response = await client.delete(f"{BASE}/1/modifications/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
        test_modification: ContractModification,
    ):
        response = await client.delete(
            f"{BASE}/{test_contract.id}/modifications/{test_modification.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Modification deleted"

    @pytest.mark.asyncio
    async def test_delete_contract_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.delete(f"{BASE}/99999/modifications/1", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_mod_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
    ):
        response = await client.delete(
            f"{BASE}/{test_contract.id}/modifications/99999",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_contract: ContractAward,
        test_modification: ContractModification,
    ):
        other_user = User(
            email="idor_mod@example.com",
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
            f"{BASE}/{test_contract.id}/modifications/{test_modification.id}",
            headers=headers,
        )
        assert response.status_code == 404
