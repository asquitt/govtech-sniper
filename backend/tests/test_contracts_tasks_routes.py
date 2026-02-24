"""
Integration tests for contracts/tasks.py:
  - GET    /contracts/{contract_id}/tasks
  - POST   /contracts/{contract_id}/tasks
  - PATCH  /contracts/tasks/{task_id}
  - DELETE /contracts/tasks/{task_id}
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contract import ContractAward, ContractTask
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password

BASE = "/api/v1/contracts"


@pytest_asyncio.fixture
async def test_contract(db_session: AsyncSession, test_user: User) -> ContractAward:
    contract = ContractAward(
        user_id=test_user.id,
        contract_number="W912HV-24-C-0003",
        title="Tasks Test Contract",
    )
    db_session.add(contract)
    await db_session.commit()
    await db_session.refresh(contract)
    return contract


@pytest_asyncio.fixture
async def test_task(db_session: AsyncSession, test_contract: ContractAward) -> ContractTask:
    task = ContractTask(
        contract_id=test_contract.id,
        title="Submit monthly invoice",
        notes="Due by the 5th.",
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


class TestListTasks:
    """Tests for GET /contracts/{contract_id}/tasks."""

    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client: AsyncClient):
        response = await client.get(f"{BASE}/1/tasks")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_empty(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
    ):
        response = await client.get(f"{BASE}/{test_contract.id}/tasks", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_returns_tasks(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
        test_task: ContractTask,
    ):
        response = await client.get(f"{BASE}/{test_contract.id}/tasks", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Submit monthly invoice"
        assert data[0]["is_complete"] is False

    @pytest.mark.asyncio
    async def test_list_contract_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(f"{BASE}/99999/tasks", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_contract: ContractAward,
    ):
        other_user = User(
            email="other_task@example.com",
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

        response = await client.get(f"{BASE}/{test_contract.id}/tasks", headers=headers)
        assert response.status_code == 404


class TestCreateTask:
    """Tests for POST /contracts/{contract_id}/tasks."""

    @pytest.mark.asyncio
    async def test_create_requires_auth(self, client: AsyncClient):
        response = await client.post(f"{BASE}/1/tasks", json={"title": "X"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
    ):
        payload = {
            "title": "Prepare quarterly review",
            "due_date": "2025-03-31",
            "notes": "Coordinate with PM.",
        }
        response = await client.post(
            f"{BASE}/{test_contract.id}/tasks",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Prepare quarterly review"
        assert data["contract_id"] == test_contract.id
        assert data["is_complete"] is False

    @pytest.mark.asyncio
    async def test_create_minimal(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
    ):
        payload = {"title": "Simple task"}
        response = await client.post(
            f"{BASE}/{test_contract.id}/tasks",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_create_contract_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            f"{BASE}/99999/tasks",
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
            f"{BASE}/{test_contract.id}/tasks",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestUpdateTask:
    """Tests for PATCH /contracts/tasks/{task_id}."""

    @pytest.mark.asyncio
    async def test_update_requires_auth(self, client: AsyncClient):
        response = await client.patch(f"{BASE}/tasks/1", json={"title": "X"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_task: ContractTask,
    ):
        payload = {"title": "Updated task", "is_complete": True}
        response = await client.patch(
            f"{BASE}/tasks/{test_task.id}",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated task"
        assert data["is_complete"] is True

    @pytest.mark.asyncio
    async def test_update_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.patch(
            f"{BASE}/tasks/99999",
            json={"title": "X"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_task: ContractTask,
    ):
        other_user = User(
            email="idor_task@example.com",
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
            f"{BASE}/tasks/{test_task.id}",
            json={"title": "Hacked"},
            headers=headers,
        )
        assert response.status_code == 404


class TestDeleteTask:
    """Tests for DELETE /contracts/tasks/{task_id}."""

    @pytest.mark.asyncio
    async def test_delete_requires_auth(self, client: AsyncClient):
        response = await client.delete(f"{BASE}/tasks/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_task: ContractTask,
    ):
        response = await client.delete(f"{BASE}/tasks/{test_task.id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["message"] == "Task deleted"

    @pytest.mark.asyncio
    async def test_delete_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.delete(f"{BASE}/tasks/99999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_task: ContractTask,
    ):
        other_user = User(
            email="idor_task2@example.com",
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

        response = await client.delete(f"{BASE}/tasks/{test_task.id}", headers=headers)
        assert response.status_code == 404
