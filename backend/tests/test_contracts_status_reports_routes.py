"""
Integration tests for contracts/status_reports.py:
  - GET    /contracts/{contract_id}/status-reports
  - GET    /contracts/{contract_id}/status-reports/{report_id}/export
  - POST   /contracts/{contract_id}/status-reports
  - PATCH  /contracts/status-reports/{report_id}
  - DELETE /contracts/status-reports/{report_id}
"""

from datetime import date

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contract import ContractAward, ContractStatusReport
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password

BASE = "/api/v1/contracts"


@pytest_asyncio.fixture
async def test_contract(db_session: AsyncSession, test_user: User) -> ContractAward:
    contract = ContractAward(
        user_id=test_user.id,
        contract_number="W912HV-24-C-0006",
        title="Status Reports Test Contract",
    )
    db_session.add(contract)
    await db_session.commit()
    await db_session.refresh(contract)
    return contract


@pytest_asyncio.fixture
async def test_report(
    db_session: AsyncSession, test_contract: ContractAward
) -> ContractStatusReport:
    report = ContractStatusReport(
        contract_id=test_contract.id,
        period_start=date(2024, 1, 1),
        period_end=date(2024, 1, 31),
        summary="January progress summary.",
        accomplishments="Completed milestone 1.",
        risks="Budget pressure from subcontractor delays.",
        next_steps="Begin milestone 2 planning.",
    )
    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)
    return report


class TestListStatusReports:
    """Tests for GET /contracts/{contract_id}/status-reports."""

    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client: AsyncClient):
        response = await client.get(f"{BASE}/1/status-reports")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_empty(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
    ):
        response = await client.get(
            f"{BASE}/{test_contract.id}/status-reports", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_returns_reports(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
        test_report: ContractStatusReport,
    ):
        response = await client.get(
            f"{BASE}/{test_contract.id}/status-reports", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["summary"] == "January progress summary."

    @pytest.mark.asyncio
    async def test_list_contract_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(f"{BASE}/99999/status-reports", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_contract: ContractAward,
    ):
        other_user = User(
            email="other_sr@example.com",
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

        response = await client.get(f"{BASE}/{test_contract.id}/status-reports", headers=headers)
        assert response.status_code == 404


class TestExportStatusReport:
    """Tests for GET /contracts/{contract_id}/status-reports/{report_id}/export."""

    @pytest.mark.asyncio
    async def test_export_requires_auth(self, client: AsyncClient):
        response = await client.get(f"{BASE}/1/status-reports/1/export")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_export_markdown(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
        test_report: ContractStatusReport,
    ):
        response = await client.get(
            f"{BASE}/{test_contract.id}/status-reports/{test_report.id}/export?format=markdown",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        body = response.text
        assert "# Status Report" in body
        assert "January progress summary." in body
        assert "Completed milestone 1." in body

    @pytest.mark.asyncio
    async def test_export_json(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
        test_report: ContractStatusReport,
    ):
        response = await client.get(
            f"{BASE}/{test_contract.id}/status-reports/{test_report.id}/export?format=json",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
        data = response.json()
        assert data["summary"] == "January progress summary."

    @pytest.mark.asyncio
    async def test_export_default_is_markdown(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
        test_report: ContractStatusReport,
    ):
        response = await client.get(
            f"{BASE}/{test_contract.id}/status-reports/{test_report.id}/export",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_export_invalid_format(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
        test_report: ContractStatusReport,
    ):
        response = await client.get(
            f"{BASE}/{test_contract.id}/status-reports/{test_report.id}/export?format=pdf",
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_export_contract_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(f"{BASE}/99999/status-reports/1/export", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_export_report_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
    ):
        response = await client.get(
            f"{BASE}/{test_contract.id}/status-reports/99999/export",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestCreateStatusReport:
    """Tests for POST /contracts/{contract_id}/status-reports."""

    @pytest.mark.asyncio
    async def test_create_requires_auth(self, client: AsyncClient):
        response = await client.post(f"{BASE}/1/status-reports", json={})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
    ):
        payload = {
            "period_start": "2024-02-01",
            "period_end": "2024-02-28",
            "summary": "February progress.",
            "accomplishments": "Deployed v2.0.",
            "risks": "None identified.",
            "next_steps": "Begin UAT.",
        }
        response = await client.post(
            f"{BASE}/{test_contract.id}/status-reports",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["summary"] == "February progress."
        assert data["contract_id"] == test_contract.id

    @pytest.mark.asyncio
    async def test_create_minimal(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
    ):
        response = await client.post(
            f"{BASE}/{test_contract.id}/status-reports",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_create_contract_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(f"{BASE}/99999/status-reports", json={}, headers=auth_headers)
        assert response.status_code == 404


class TestUpdateStatusReport:
    """Tests for PATCH /contracts/status-reports/{report_id}."""

    @pytest.mark.asyncio
    async def test_update_requires_auth(self, client: AsyncClient):
        response = await client.patch(f"{BASE}/status-reports/1", json={"summary": "X"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_report: ContractStatusReport,
    ):
        payload = {"summary": "Updated summary.", "risks": "New risk identified."}
        response = await client.patch(
            f"{BASE}/status-reports/{test_report.id}",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["summary"] == "Updated summary."
        assert data["risks"] == "New risk identified."

    @pytest.mark.asyncio
    async def test_update_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.patch(
            f"{BASE}/status-reports/99999",
            json={"summary": "X"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_report: ContractStatusReport,
    ):
        other_user = User(
            email="idor_sr@example.com",
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
            f"{BASE}/status-reports/{test_report.id}",
            json={"summary": "Hacked"},
            headers=headers,
        )
        assert response.status_code == 404


class TestDeleteStatusReport:
    """Tests for DELETE /contracts/status-reports/{report_id}."""

    @pytest.mark.asyncio
    async def test_delete_requires_auth(self, client: AsyncClient):
        response = await client.delete(f"{BASE}/status-reports/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_report: ContractStatusReport,
    ):
        response = await client.delete(
            f"{BASE}/status-reports/{test_report.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Status report deleted"

    @pytest.mark.asyncio
    async def test_delete_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.delete(f"{BASE}/status-reports/99999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_report: ContractStatusReport,
    ):
        other_user = User(
            email="idor_sr2@example.com",
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
            f"{BASE}/status-reports/{test_report.id}",
            headers=headers,
        )
        assert response.status_code == 404
