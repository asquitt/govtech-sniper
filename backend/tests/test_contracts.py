"""
RFP Sniper - Contracts Tests
============================
Tests for contract CRUD and deliverables.
"""

import pytest
from httpx import AsyncClient


class TestContracts:
    @pytest.mark.asyncio
    async def test_contract_lifecycle(self, client: AsyncClient, auth_headers: dict):
        # Create contract
        response = await client.post(
            "/api/v1/contracts",
            headers=auth_headers,
            json={
                "contract_number": "CN-001",
                "title": "Test Contract",
                "agency": "Test Agency",
                "status": "active",
            },
        )
        assert response.status_code == 200
        contract = response.json()

        # List contracts
        response = await client.get("/api/v1/contracts", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

        # Update contract
        response = await client.patch(
            f"/api/v1/contracts/{contract['id']}",
            headers=auth_headers,
            json={"status": "at_risk"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "at_risk"

        # Create deliverable
        response = await client.post(
            f"/api/v1/contracts/{contract['id']}/deliverables",
            headers=auth_headers,
            json={"title": "Kickoff Deck", "status": "pending"},
        )
        assert response.status_code == 200

        # List deliverables
        response = await client.get(
            f"/api/v1/contracts/{contract['id']}/deliverables",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert len(response.json()) == 1

        # Create task
        response = await client.post(
            f"/api/v1/contracts/{contract['id']}/tasks",
            headers=auth_headers,
            json={"title": "Kickoff meeting"},
        )
        assert response.status_code == 200

        # Create CPARS review
        response = await client.post(
            f"/api/v1/contracts/{contract['id']}/cpars",
            headers=auth_headers,
            json={"overall_rating": "Excellent", "notes": "On track"},
        )
        assert response.status_code == 200

        # Create status report
        response = await client.post(
            f"/api/v1/contracts/{contract['id']}/status-reports",
            headers=auth_headers,
            json={
                "period_start": "2025-01-01",
                "period_end": "2025-01-31",
                "summary": "Delivered milestones",
                "risks": "None",
                "next_steps": "Prepare February report",
            },
        )
        assert response.status_code == 200

        # List status reports
        response = await client.get(
            f"/api/v1/contracts/{contract['id']}/status-reports",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert len(response.json()) == 1
