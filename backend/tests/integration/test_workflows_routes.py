"""
Workflows Routes Integration Tests
=====================================
Tests for workflow rule CRUD, execution, and test/dry-run.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.workflow import WorkflowRule

# =============================================================================
# Helpers
# =============================================================================


@pytest.fixture
async def test_rule(db_session: AsyncSession, test_user: User) -> WorkflowRule:
    rule = WorkflowRule(
        user_id=test_user.id,
        name="Auto-assign analyst",
        trigger_type="rfp_uploaded",
        conditions=[{"field": "agency", "operator": "eq", "value": "DoD"}],
        actions=[{"type": "assign", "user_id": 1}],
        priority=100,
        is_enabled=True,
    )
    db_session.add(rule)
    await db_session.commit()
    await db_session.refresh(rule)
    return rule


# =============================================================================
# POST /workflows/rules — create rule
# =============================================================================


class TestCreateRule:
    @pytest.mark.asyncio
    async def test_create_rule_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/workflows/rules",
            json={
                "name": "Rule",
                "trigger_type": "rfp_uploaded",
                "conditions": [],
                "actions": [],
            },
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_create_rule_success(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/workflows/rules",
            json={
                "name": "New Rule",
                "trigger_type": "rfp_uploaded",
                "conditions": [{"field": "agency", "operator": "eq", "value": "GSA"}],
                "actions": [{"type": "notify", "message": "New GSA RFP"}],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "New Rule"
        assert data["trigger_type"] == "rfp_uploaded"
        assert data["is_enabled"] is True


# =============================================================================
# GET /workflows/rules — list rules
# =============================================================================


class TestListRules:
    @pytest.mark.asyncio
    async def test_list_rules_empty(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/workflows/rules", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_list_rules_with_data(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rule: WorkflowRule,
    ):
        resp = await client.get("/api/v1/workflows/rules", headers=auth_headers)
        data = resp.json()
        assert data["total"] >= 1
        assert data["items"][0]["name"] == "Auto-assign analyst"

    @pytest.mark.asyncio
    async def test_list_rules_pagination(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get(
            "/api/v1/workflows/rules?limit=5&offset=0",
            headers=auth_headers,
        )
        assert resp.status_code == 200


# =============================================================================
# GET /workflows/rules/{id} — get single rule
# =============================================================================


class TestGetRule:
    @pytest.mark.asyncio
    async def test_get_rule_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rule: WorkflowRule,
    ):
        resp = await client.get(
            f"/api/v1/workflows/rules/{test_rule.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == test_rule.id

    @pytest.mark.asyncio
    async def test_get_rule_not_found(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/workflows/rules/99999", headers=auth_headers)
        assert resp.status_code == 404


# =============================================================================
# PATCH /workflows/rules/{id} — update rule
# =============================================================================


class TestUpdateRule:
    @pytest.mark.asyncio
    async def test_update_rule_name(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rule: WorkflowRule,
    ):
        resp = await client.patch(
            f"/api/v1/workflows/rules/{test_rule.id}",
            json={"name": "Renamed Rule"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed Rule"

    @pytest.mark.asyncio
    async def test_update_rule_disable(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rule: WorkflowRule,
    ):
        resp = await client.patch(
            f"/api/v1/workflows/rules/{test_rule.id}",
            json={"is_enabled": False},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["is_enabled"] is False


# =============================================================================
# DELETE /workflows/rules/{id} — delete rule
# =============================================================================


class TestDeleteRule:
    @pytest.mark.asyncio
    async def test_delete_rule_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rule: WorkflowRule,
    ):
        resp = await client.delete(
            f"/api/v1/workflows/rules/{test_rule.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_rule_not_found(self, client: AsyncClient, auth_headers: dict):
        resp = await client.delete("/api/v1/workflows/rules/99999", headers=auth_headers)
        assert resp.status_code == 404


# =============================================================================
# POST /workflows/rules/{id}/test — dry-run
# =============================================================================


class TestDryRunRule:
    @pytest.mark.asyncio
    async def test_dry_run_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rule: WorkflowRule,
    ):
        resp = await client.post(
            f"/api/v1/workflows/rules/{test_rule.id}/test",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "would_match" in data or "rule_name" in data


# =============================================================================
# GET /workflows/executions — execution history
# =============================================================================


class TestListExecutions:
    @pytest.mark.asyncio
    async def test_list_executions_empty(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/workflows/executions", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_list_executions_filter_by_rule(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rule: WorkflowRule,
    ):
        resp = await client.get(
            f"/api/v1/workflows/executions?rule_id={test_rule.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
