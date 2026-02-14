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

    @pytest.mark.asyncio
    async def test_bid_scenario_simulator_returns_default_stress_tests(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
    ):
        criteria = [
            {"name": "technical_capability", "weight": 15, "score": 78},
            {"name": "past_performance", "weight": 12, "score": 75},
            {"name": "price_competitiveness", "weight": 10, "score": 70},
            {"name": "staffing_availability", "weight": 10, "score": 72},
            {"name": "clearance_requirements", "weight": 10, "score": 80},
            {"name": "set_aside_eligibility", "weight": 8, "score": 82},
            {"name": "relationship_with_agency", "weight": 8, "score": 74},
            {"name": "competitive_landscape", "weight": 7, "score": 68},
            {"name": "geographic_fit", "weight": 5, "score": 79},
            {"name": "contract_vehicle_access", "weight": 5, "score": 77},
            {"name": "teaming_strength", "weight": 5, "score": 66},
            {"name": "proposal_timeline", "weight": 5, "score": 71},
        ]
        vote_response = await client.post(
            f"/api/v1/capture/scorecards/{test_rfp.id}/vote",
            headers=auth_headers,
            json={
                "criteria_scores": criteria,
                "overall_score": 74,
                "recommendation": "bid",
                "reasoning": "Strong baseline fit across core dimensions.",
            },
        )
        assert vote_response.status_code == 200

        response = await client.post(
            f"/api/v1/capture/scorecards/{test_rfp.id}/scenario-simulator",
            headers=auth_headers,
            json={},
        )
        assert response.status_code == 200

        payload = response.json()
        assert payload["rfp_id"] == test_rfp.id
        assert payload["baseline"]["recommendation"] == "bid"
        assert payload["baseline"]["overall_score"] > 0
        assert "FAR 15.305" in payload["baseline"]["scoring_method"]
        assert len(payload["scenarios"]) >= 3
        assert all("decision_risk" in item for item in payload["scenarios"])
        assert all("driver_summary" in item for item in payload["scenarios"])
        assert all("scoring_rationale" in item for item in payload["scenarios"])
        assert all("criteria_scores" in item for item in payload["scenarios"])

    @pytest.mark.asyncio
    async def test_bid_scenario_simulator_supports_custom_adjustments_and_ignored_fields(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
    ):
        criteria = [
            {"name": "technical_capability", "weight": 15, "score": 80},
            {"name": "past_performance", "weight": 12, "score": 80},
            {"name": "price_competitiveness", "weight": 10, "score": 80},
            {"name": "staffing_availability", "weight": 10, "score": 80},
            {"name": "clearance_requirements", "weight": 10, "score": 80},
            {"name": "set_aside_eligibility", "weight": 8, "score": 80},
            {"name": "relationship_with_agency", "weight": 8, "score": 80},
            {"name": "competitive_landscape", "weight": 7, "score": 80},
            {"name": "geographic_fit", "weight": 5, "score": 80},
            {"name": "contract_vehicle_access", "weight": 5, "score": 80},
            {"name": "teaming_strength", "weight": 5, "score": 80},
            {"name": "proposal_timeline", "weight": 5, "score": 80},
        ]
        vote_response = await client.post(
            f"/api/v1/capture/scorecards/{test_rfp.id}/vote",
            headers=auth_headers,
            json={
                "criteria_scores": criteria,
                "overall_score": 80,
                "recommendation": "bid",
                "reasoning": "Baseline assumes strong pursuit conditions.",
            },
        )
        assert vote_response.status_code == 200

        response = await client.post(
            f"/api/v1/capture/scorecards/{test_rfp.id}/scenario-simulator",
            headers=auth_headers,
            json={
                "scenarios": [
                    {
                        "name": "Adversarial downside",
                        "notes": "Severe downside case across evaluation factors.",
                        "adjustments": [
                            {"criterion": "technical_capability", "delta": -55},
                            {"criterion": "past_performance", "delta": -55},
                            {"criterion": "price_competitiveness", "delta": -55},
                            {"criterion": "staffing_availability", "delta": -55},
                            {"criterion": "clearance_requirements", "delta": -55},
                            {"criterion": "set_aside_eligibility", "delta": -55},
                            {"criterion": "relationship_with_agency", "delta": -55},
                            {"criterion": "competitive_landscape", "delta": -55},
                            {"criterion": "geographic_fit", "delta": -55},
                            {"criterion": "contract_vehicle_access", "delta": -55},
                            {"criterion": "teaming_strength", "delta": -55},
                            {"criterion": "proposal_timeline", "delta": -55},
                            {"criterion": "unknown_dimension", "delta": -25},
                        ],
                    }
                ]
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert len(payload["scenarios"]) == 1
        scenario = payload["scenarios"][0]
        assert scenario["name"] == "Adversarial downside"
        assert scenario["recommendation"] == "no_bid"
        assert scenario["recommendation_changed"] is True
        assert scenario["overall_score"] < 45
        assert scenario["decision_risk"] in {"low", "medium", "high"}
        assert len(scenario["ignored_adjustments"]) == 1
        assert scenario["ignored_adjustments"][0]["criterion"] == "unknown_dimension"
        assert "FAR 15.305" in scenario["scoring_rationale"]["method"]
        assert scenario["scoring_rationale"]["dominant_factors"][0]["far_reference"].startswith(
            "FAR"
        )
