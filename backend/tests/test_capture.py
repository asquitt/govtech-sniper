"""
RFP Sniper - Capture Tests
==========================
Tests for capture plans, gate reviews, and teaming partners.
"""

import pytest
from httpx import AsyncClient

from app.models.rfp import RFP


class TestCapture:
    @pytest.mark.asyncio
    async def test_capture_plan_and_gate_review(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
    ):
        # Create capture plan
        response = await client.post(
            "/api/v1/capture/plans",
            headers=auth_headers,
            json={
                "rfp_id": test_rfp.id,
                "stage": "qualified",
                "bid_decision": "bid",
                "win_probability": 65,
                "notes": "Strong fit",
            },
        )
        assert response.status_code == 200
        plan = response.json()
        assert plan["rfp_id"] == test_rfp.id

        # Get capture plan
        response = await client.get(
            f"/api/v1/capture/plans/{test_rfp.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Update capture plan
        response = await client.patch(
            f"/api/v1/capture/plans/{plan['id']}",
            headers=auth_headers,
            json={"stage": "proposal"},
        )
        assert response.status_code == 200
        assert response.json()["stage"] == "proposal"

        # List capture plans
        response = await client.get(
            "/api/v1/capture/plans",
            headers=auth_headers,
            params={"include_rfp": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["plans"][0]["rfp_id"] == test_rfp.id

        response = await client.get(
            f"/api/v1/capture/plans/{plan['id']}/match-insight",
            headers=auth_headers,
        )
        assert response.status_code == 200
        insight = response.json()
        assert insight["plan_id"] == plan["id"]

        # Create gate review
        response = await client.post(
            "/api/v1/capture/gate-reviews",
            headers=auth_headers,
            json={
                "rfp_id": test_rfp.id,
                "stage": "qualified",
                "decision": "bid",
                "notes": "Proceed",
            },
        )
        assert response.status_code == 200

        # List gate reviews
        response = await client.get(
            "/api/v1/capture/gate-reviews",
            headers=auth_headers,
            params={"rfp_id": test_rfp.id},
        )
        assert response.status_code == 200
        assert len(response.json()) == 1

    @pytest.mark.asyncio
    async def test_teaming_partners(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
    ):
        # Create partner
        response = await client.post(
            "/api/v1/capture/partners",
            headers=auth_headers,
            json={"name": "Acme Sub", "partner_type": "sub"},
        )
        assert response.status_code == 200
        partner_id = response.json()["id"]

        # Link partner
        response = await client.post(
            "/api/v1/capture/partners/link",
            headers=auth_headers,
            json={"rfp_id": test_rfp.id, "partner_id": partner_id, "role": "Subcontractor"},
        )
        assert response.status_code == 200

        # List links
        response = await client.get(
            "/api/v1/capture/partners/links",
            headers=auth_headers,
            params={"rfp_id": test_rfp.id},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    @pytest.mark.asyncio
    async def test_competitors(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
    ):
        response = await client.post(
            "/api/v1/capture/competitors",
            headers=auth_headers,
            json={
                "rfp_id": test_rfp.id,
                "name": "Competitor A",
                "incumbent": True,
                "strengths": "Past performance",
            },
        )
        assert response.status_code == 200
        competitor_id = response.json()["id"]

        response = await client.get(
            "/api/v1/capture/competitors",
            headers=auth_headers,
            params={"rfp_id": test_rfp.id},
        )
        assert response.status_code == 200
        assert len(response.json()) == 1

        response = await client.patch(
            f"/api/v1/capture/competitors/{competitor_id}",
            headers=auth_headers,
            json={"notes": "Updated notes"},
        )
        assert response.status_code == 200
        assert response.json()["notes"] == "Updated notes"

        response = await client.delete(
            f"/api/v1/capture/competitors/{competitor_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_capture_custom_fields(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
    ):
        # Create capture plan
        response = await client.post(
            "/api/v1/capture/plans",
            headers=auth_headers,
            json={"rfp_id": test_rfp.id},
        )
        assert response.status_code == 200
        plan_id = response.json()["id"]

        # Create custom field
        response = await client.post(
            "/api/v1/capture/fields",
            headers=auth_headers,
            json={
                "name": "Customer Priority",
                "field_type": "select",
                "options": ["High", "Medium", "Low"],
                "is_required": True,
            },
        )
        assert response.status_code == 200
        field_id = response.json()["id"]

        # List fields
        response = await client.get("/api/v1/capture/fields", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) >= 1

        # Update plan fields
        response = await client.put(
            f"/api/v1/capture/plans/{plan_id}/fields",
            headers=auth_headers,
            json=[{"field_id": field_id, "value": "High"}],
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["fields"][0]["value"] == "High"

        # List plan fields
        response = await client.get(
            f"/api/v1/capture/plans/{plan_id}/fields",
            headers=auth_headers,
        )
        assert response.status_code == 200
        fields = response.json()["fields"]
        assert any(field["field"]["id"] == field_id for field in fields)
