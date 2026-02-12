"""Integration coverage for workflow execution engine and capture triggers."""

from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlmodel import select

from app.models.rfp import RFP
from app.models.workflow import WorkflowExecution


class TestWorkflowExecution:
    @pytest.mark.asyncio
    async def test_capture_create_triggers_move_stage_and_notification(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
        db_session,
    ):
        create_rule = await client.post(
            "/api/v1/workflows/rules",
            headers=auth_headers,
            json={
                "name": "Promote high confidence capture",
                "trigger_type": "rfp_created",
                "conditions": [
                    {
                        "field": "win_probability",
                        "operator": "gt",
                        "value": 60,
                    }
                ],
                "actions": [
                    {"action_type": "move_stage", "params": {"stage": "pursuit"}},
                    {
                        "action_type": "send_notification",
                        "params": {
                            "title": "Capture promoted",
                            "message": "Automation advanced this opportunity to pursuit.",
                        },
                    },
                ],
                "priority": 10,
            },
        )
        assert create_rule.status_code == 200

        create_plan = await client.post(
            "/api/v1/capture/plans",
            headers=auth_headers,
            json={
                "rfp_id": test_rfp.id,
                "stage": "identified",
                "bid_decision": "pending",
                "win_probability": 80,
                "notes": "seed",
            },
        )
        assert create_plan.status_code == 200
        plan_id = create_plan.json()["id"]

        plan_response = await client.get(
            f"/api/v1/capture/plans/{test_rfp.id}",
            headers=auth_headers,
        )
        assert plan_response.status_code == 200
        assert plan_response.json()["stage"] == "pursuit"

        execution_response = await client.get(
            "/api/v1/workflows/executions",
            headers=auth_headers,
        )
        assert execution_response.status_code == 200
        payload = execution_response.json()
        assert payload["total"] >= 1
        assert any(
            item["entity_id"] == plan_id and item["status"] == "success"
            for item in payload["items"]
        )

        notifications = await client.get("/api/v1/notifications", headers=auth_headers)
        assert notifications.status_code == 200
        assert any(item["title"] == "Capture promoted" for item in notifications.json())

    @pytest.mark.asyncio
    async def test_stage_change_trigger_adds_tag_and_records_execution(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
        db_session,
    ):
        create_rule = await client.post(
            "/api/v1/workflows/rules",
            headers=auth_headers,
            json={
                "name": "Tag proposal phase",
                "trigger_type": "stage_changed",
                "conditions": [
                    {
                        "field": "stage",
                        "operator": "equals",
                        "value": "proposal",
                    }
                ],
                "actions": [
                    {"action_type": "add_tag", "params": {"tag": "proposal-phase"}},
                    {"action_type": "evaluate_teaming", "params": {}},
                ],
                "priority": 5,
            },
        )
        assert create_rule.status_code == 200

        create_plan = await client.post(
            "/api/v1/capture/plans",
            headers=auth_headers,
            json={
                "rfp_id": test_rfp.id,
                "stage": "qualified",
                "bid_decision": "pending",
                "win_probability": 52,
                "notes": "seed",
            },
        )
        assert create_plan.status_code == 200
        plan_id = create_plan.json()["id"]

        update_plan = await client.patch(
            f"/api/v1/capture/plans/{plan_id}",
            headers=auth_headers,
            json={"stage": "proposal", "notes": "advanced"},
        )
        assert update_plan.status_code == 200
        assert update_plan.json()["stage"] == "proposal"

        rfp = await db_session.get(RFP, test_rfp.id)
        assert rfp is not None
        assert "#proposal-phase" in (rfp.intel_notes or "")

        executions_result = await db_session.execute(
            select(WorkflowExecution)
            .where(
                WorkflowExecution.entity_type == "capture_plan",
                WorkflowExecution.entity_id == plan_id,
            )
            .order_by(WorkflowExecution.triggered_at.desc())
        )
        executions = executions_result.scalars().all()
        assert executions
        assert any(execution.status.value == "success" for execution in executions)

    @pytest.mark.asyncio
    async def test_manual_workflow_execute_endpoint(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
    ):
        rule = await client.post(
            "/api/v1/workflows/rules",
            headers=auth_headers,
            json={
                "name": "Manual notify",
                "trigger_type": "score_threshold",
                "conditions": [],
                "actions": [
                    {
                        "action_type": "send_notification",
                        "params": {
                            "title": "Workflow run",
                            "message": "Manual execution succeeded.",
                        },
                    }
                ],
                "priority": 1,
            },
        )
        assert rule.status_code == 200

        create_plan = await client.post(
            "/api/v1/capture/plans",
            headers=auth_headers,
            json={
                "rfp_id": test_rfp.id,
                "stage": "identified",
                "bid_decision": "pending",
                "win_probability": 45,
            },
        )
        assert create_plan.status_code == 200
        plan_id = create_plan.json()["id"]

        execute = await client.post(
            "/api/v1/workflows/execute",
            headers=auth_headers,
            json={
                "trigger_type": "score_threshold",
                "entity_type": "capture_plan",
                "entity_id": plan_id,
                "context": {"win_probability": 45, "executed_at": datetime.utcnow().isoformat()},
            },
        )
        assert execute.status_code == 200
        payload = execute.json()
        assert payload["total"] >= 1
        assert any(item["status"] == "success" for item in payload["executions"])
