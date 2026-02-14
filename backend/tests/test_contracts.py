"""
RFP Sniper - Contracts Tests
============================
Tests for contract CRUD and deliverables.
"""

import pytest
from httpx import AsyncClient


class TestContracts:
    @pytest.mark.asyncio
    async def test_contract_lifecycle(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_document,
    ):
        # Create contract
        response = await client.post(
            "/api/v1/contracts",
            headers=auth_headers,
            json={
                "contract_number": "CN-001",
                "title": "Test Contract",
                "agency": "Test Agency",
                "status": "active",
                "classification": "fci",
            },
        )
        assert response.status_code == 200
        contract = response.json()
        assert contract["classification"] == "fci"

        # List contracts
        response = await client.get("/api/v1/contracts", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

        # Update contract
        response = await client.patch(
            f"/api/v1/contracts/{contract['id']}",
            headers=auth_headers,
            json={"status": "at_risk", "classification": "cui"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "at_risk"
        assert response.json()["classification"] == "cui"

        # Create child contract under parent contract
        response = await client.post(
            "/api/v1/contracts",
            headers=auth_headers,
            json={
                "contract_number": "CN-001-TO-01",
                "title": "Task Order 1",
                "agency": "Test Agency",
                "parent_contract_id": contract["id"],
                "contract_type": "task_order",
                "status": "active",
            },
        )
        assert response.status_code == 200
        child_contract = response.json()
        assert child_contract["parent_contract_id"] == contract["id"]
        assert child_contract["contract_type"] == "task_order"

        # Circular hierarchy prevention: parent cannot point to child
        response = await client.patch(
            f"/api/v1/contracts/{contract['id']}",
            headers=auth_headers,
            json={"parent_contract_id": child_contract["id"]},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Circular contract hierarchy"

        # Self-parent prevention
        response = await client.patch(
            f"/api/v1/contracts/{contract['id']}",
            headers=auth_headers,
            json={"parent_contract_id": contract["id"]},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Contract cannot be its own parent"

        # Verify both contracts are listed
        response = await client.get("/api/v1/contracts", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

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

        # Create and delete modification
        response = await client.post(
            f"/api/v1/contracts/{contract['id']}/modifications",
            headers=auth_headers,
            json={
                "modification_number": "P0001",
                "mod_type": "funding",
                "description": "Incremental funding",
                "effective_date": "2025-02-15",
                "value_change": 250000.0,
            },
        )
        assert response.status_code == 200
        modification = response.json()
        assert modification["modification_number"] == "P0001"

        response = await client.get(
            f"/api/v1/contracts/{contract['id']}/modifications",
            headers=auth_headers,
        )
        assert response.status_code == 200
        modifications = response.json()
        assert len(modifications) == 1
        assert modifications[0]["description"] == "Incremental funding"

        response = await client.delete(
            f"/api/v1/contracts/{contract['id']}/modifications/{modification['id']}",
            headers=auth_headers,
        )
        assert response.status_code == 200

        response = await client.get(
            f"/api/v1/contracts/{contract['id']}/modifications",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json() == []

        # Create/update/delete CLIN
        response = await client.post(
            f"/api/v1/contracts/{contract['id']}/clins",
            headers=auth_headers,
            json={
                "clin_number": "0001",
                "description": "Labor support",
                "clin_type": "t_and_m",
                "unit_price": 100.0,
                "quantity": 10,
                "total_value": 1000.0,
                "funded_amount": 500.0,
            },
        )
        assert response.status_code == 200
        clin = response.json()
        assert clin["clin_number"] == "0001"

        response = await client.patch(
            f"/api/v1/contracts/{contract['id']}/clins/{clin['id']}",
            headers=auth_headers,
            json={"quantity": 12, "funded_amount": 750.0, "total_value": 1200.0},
        )
        assert response.status_code == 200
        updated_clin = response.json()
        assert updated_clin["quantity"] == 12
        assert updated_clin["funded_amount"] == 750.0

        response = await client.get(
            f"/api/v1/contracts/{contract['id']}/clins",
            headers=auth_headers,
        )
        assert response.status_code == 200
        clins = response.json()
        assert len(clins) == 1
        assert clins[0]["total_value"] == 1200.0

        response = await client.delete(
            f"/api/v1/contracts/{contract['id']}/clins/{clin['id']}",
            headers=auth_headers,
        )
        assert response.status_code == 200

        response = await client.get(
            f"/api/v1/contracts/{contract['id']}/clins",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json() == []

        # Create CPARS review
        response = await client.post(
            f"/api/v1/contracts/{contract['id']}/cpars",
            headers=auth_headers,
            json={"overall_rating": "Excellent", "notes": "On track"},
        )
        assert response.status_code == 200
        review = response.json()

        response = await client.post(
            f"/api/v1/contracts/{contract['id']}/cpars/{review['id']}/evidence",
            headers=auth_headers,
            json={
                "document_id": test_document.id,
                "citation": "CPARS supporting evidence",
                "notes": "Strong delivery record",
            },
        )
        assert response.status_code == 200
        evidence = response.json()
        assert evidence["document_id"] == test_document.id

        response = await client.get(
            f"/api/v1/contracts/{contract['id']}/cpars/{review['id']}/evidence",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert len(response.json()) == 1

        response = await client.delete(
            f"/api/v1/contracts/{contract['id']}/cpars/{review['id']}/evidence/{evidence['id']}",
            headers=auth_headers,
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
        report = response.json()

        # List status reports
        response = await client.get(
            f"/api/v1/contracts/{contract['id']}/status-reports",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert len(response.json()) == 1

        response = await client.get(
            f"/api/v1/contracts/{contract['id']}/status-reports/{report['id']}/export",
            headers=auth_headers,
        )
        assert response.status_code == 200
