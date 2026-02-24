"""
Integration tests for workflows.py:
  - POST   /workflows/rules
  - GET    /workflows/rules
  - GET    /workflows/rules/{rule_id}
  - PATCH  /workflows/rules/{rule_id}
  - DELETE /workflows/rules/{rule_id}
  - POST   /workflows/rules/{rule_id}/test
  - GET    /workflows/executions
  - POST   /workflows/execute
"""

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.workflow import TriggerType, WorkflowRule

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_RULE_PAYLOAD = {
    "name": "Auto-move high-score RFPs",
    "trigger_type": "rfp_created",
    "conditions": [{"field": "recommendation_score", "operator": "gt", "value": 75}],
    "actions": [{"action_type": "move_stage", "params": {"stage": "active_pursuit"}}],
    "priority": 10,
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def test_rule(db_session: AsyncSession, test_user: User) -> WorkflowRule:
    """Create a workflow rule for the test user."""
    rule = WorkflowRule(
        user_id=test_user.id,
        name="Test Rule",
        trigger_type=TriggerType.RFP_CREATED,
        conditions=[{"field": "status", "operator": "equals", "value": "new"}],
        actions=[{"action_type": "send_notification", "params": {"message": "New RFP!"}}],
        priority=5,
        is_enabled=True,
    )
    db_session.add(rule)
    await db_session.commit()
    await db_session.refresh(rule)
    return rule


# ---------------------------------------------------------------------------
# Create rule tests
# ---------------------------------------------------------------------------


class TestWorkflowRuleCreate:
    """Tests for POST /workflows/rules."""

    @pytest.mark.asyncio
    async def test_create_rule_requires_auth(self, client: AsyncClient):
        """Rule creation returns 401 without auth."""
        response = await client.post("/api/v1/workflows/rules", json=VALID_RULE_PAYLOAD)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_rule_success(self, client: AsyncClient, auth_headers: dict):
        """Authenticated user can create a workflow rule."""
        response = await client.post(
            "/api/v1/workflows/rules",
            headers=auth_headers,
            json=VALID_RULE_PAYLOAD,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == VALID_RULE_PAYLOAD["name"]
        assert data["trigger_type"] == "rfp_created"
        assert data["is_enabled"] is True
        assert data["priority"] == 10

    @pytest.mark.asyncio
    async def test_create_rule_default_priority(self, client: AsyncClient, auth_headers: dict):
        """Rule defaults to priority 0 when not supplied."""
        response = await client.post(
            "/api/v1/workflows/rules",
            headers=auth_headers,
            json={
                "name": "No priority rule",
                "trigger_type": "stage_changed",
                "conditions": [],
                "actions": [],
            },
        )
        assert response.status_code == 200
        assert response.json()["priority"] == 0

    @pytest.mark.asyncio
    async def test_create_rule_missing_trigger_type(self, client: AsyncClient, auth_headers: dict):
        """Rule creation without trigger_type returns 422."""
        response = await client.post(
            "/api/v1/workflows/rules",
            headers=auth_headers,
            json={"name": "Bad Rule"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_rule_invalid_trigger_type(self, client: AsyncClient, auth_headers: dict):
        """Rule creation with unknown trigger_type returns 422."""
        response = await client.post(
            "/api/v1/workflows/rules",
            headers=auth_headers,
            json={
                "name": "Invalid Trigger",
                "trigger_type": "not_a_real_trigger",
                "conditions": [],
                "actions": [],
            },
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# List rules tests
# ---------------------------------------------------------------------------


class TestWorkflowRuleList:
    """Tests for GET /workflows/rules."""

    @pytest.mark.asyncio
    async def test_list_rules_requires_auth(self, client: AsyncClient):
        """Rule listing returns 401 without auth."""
        response = await client.get("/api/v1/workflows/rules")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_rules_empty(self, client: AsyncClient, auth_headers: dict):
        """Empty list returned when no rules exist."""
        response = await client.get("/api/v1/workflows/rules", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_rules_with_data(
        self, client: AsyncClient, auth_headers: dict, test_rule: WorkflowRule
    ):
        """List returns existing rules with total count."""
        response = await client.get("/api/v1/workflows/rules", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == test_rule.name

    @pytest.mark.asyncio
    async def test_list_rules_pagination(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        """List rules respects limit and offset."""
        for i in range(5):
            rule = WorkflowRule(
                user_id=test_user.id,
                name=f"Rule {i}",
                trigger_type=TriggerType.RFP_CREATED,
                conditions=[],
                actions=[],
                priority=i,
            )
            db_session.add(rule)
        await db_session.commit()

        resp1 = await client.get("/api/v1/workflows/rules?limit=3&offset=0", headers=auth_headers)
        assert resp1.status_code == 200
        assert len(resp1.json()["items"]) == 3

        resp2 = await client.get("/api/v1/workflows/rules?limit=3&offset=3", headers=auth_headers)
        assert resp2.status_code == 200
        assert len(resp2.json()["items"]) == 2


# ---------------------------------------------------------------------------
# Get rule tests
# ---------------------------------------------------------------------------


class TestWorkflowRuleGet:
    """Tests for GET /workflows/rules/{rule_id}."""

    @pytest.mark.asyncio
    async def test_get_rule_success(
        self, client: AsyncClient, auth_headers: dict, test_rule: WorkflowRule
    ):
        """Can retrieve a rule by ID."""
        response = await client.get(f"/api/v1/workflows/rules/{test_rule.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_rule.id
        assert data["name"] == test_rule.name

    @pytest.mark.asyncio
    async def test_get_rule_not_found(self, client: AsyncClient, auth_headers: dict):
        """Returns 404 for non-existent rule."""
        response = await client.get("/api/v1/workflows/rules/999999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_rule_other_user_not_found(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_rule: WorkflowRule,
    ):
        """Another user cannot see this user's rule (returns 404)."""
        from app.services.auth_service import create_token_pair, hash_password

        other = User(
            email="other@example.com",
            hashed_password=hash_password("OtherPass123!"),
            full_name="Other",
            company_name="Other Co",
            tier="free",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other)
        await db_session.commit()
        await db_session.refresh(other)

        tokens = create_token_pair(other.id, other.email, other.tier)
        other_headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.get(
            f"/api/v1/workflows/rules/{test_rule.id}", headers=other_headers
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Update rule tests
# ---------------------------------------------------------------------------


class TestWorkflowRuleUpdate:
    """Tests for PATCH /workflows/rules/{rule_id}."""

    @pytest.mark.asyncio
    async def test_update_rule_name(
        self, client: AsyncClient, auth_headers: dict, test_rule: WorkflowRule
    ):
        """Can update a rule's name."""
        response = await client.patch(
            f"/api/v1/workflows/rules/{test_rule.id}",
            headers=auth_headers,
            json={"name": "Updated Rule Name"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Rule Name"

    @pytest.mark.asyncio
    async def test_enable_disable_rule(
        self, client: AsyncClient, auth_headers: dict, test_rule: WorkflowRule
    ):
        """Can disable then re-enable a rule."""
        # Disable
        resp = await client.patch(
            f"/api/v1/workflows/rules/{test_rule.id}",
            headers=auth_headers,
            json={"is_enabled": False},
        )
        assert resp.status_code == 200
        assert resp.json()["is_enabled"] is False

        # Re-enable
        resp = await client.patch(
            f"/api/v1/workflows/rules/{test_rule.id}",
            headers=auth_headers,
            json={"is_enabled": True},
        )
        assert resp.status_code == 200
        assert resp.json()["is_enabled"] is True

    @pytest.mark.asyncio
    async def test_update_rule_not_found(self, client: AsyncClient, auth_headers: dict):
        """PATCH on non-existent rule returns 404."""
        response = await client.patch(
            "/api/v1/workflows/rules/999999",
            headers=auth_headers,
            json={"name": "Ghost"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_rule_requires_auth(self, client: AsyncClient, test_rule: WorkflowRule):
        """PATCH returns 401 without auth."""
        response = await client.patch(
            f"/api/v1/workflows/rules/{test_rule.id}",
            json={"name": "No auth"},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Delete rule tests
# ---------------------------------------------------------------------------


class TestWorkflowRuleDelete:
    """Tests for DELETE /workflows/rules/{rule_id}."""

    @pytest.mark.asyncio
    async def test_delete_rule_success(
        self, client: AsyncClient, auth_headers: dict, test_rule: WorkflowRule
    ):
        """Can delete a rule."""
        response = await client.delete(
            f"/api/v1/workflows/rules/{test_rule.id}", headers=auth_headers
        )
        assert response.status_code == 200
        assert "deleted" in response.json().get("message", "").lower()

    @pytest.mark.asyncio
    async def test_delete_rule_not_found(self, client: AsyncClient, auth_headers: dict):
        """DELETE on non-existent rule returns 404."""
        response = await client.delete("/api/v1/workflows/rules/999999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_rule_removes_it(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rule: WorkflowRule,
    ):
        """After deletion, GET returns 404."""
        await client.delete(f"/api/v1/workflows/rules/{test_rule.id}", headers=auth_headers)
        response = await client.get(f"/api/v1/workflows/rules/{test_rule.id}", headers=auth_headers)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Test (dry-run) rule tests
# ---------------------------------------------------------------------------


class TestWorkflowRuleTest:
    """Tests for POST /workflows/rules/{rule_id}/test."""

    @pytest.mark.asyncio
    async def test_rule_test_enabled(
        self, client: AsyncClient, auth_headers: dict, test_rule: WorkflowRule
    ):
        """Test endpoint returns would_match=1 for an enabled rule."""
        response = await client.post(
            f"/api/v1/workflows/rules/{test_rule.id}/test",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "would_match" in data
        assert data["would_match"] == 1
        assert "sample_results" in data

    @pytest.mark.asyncio
    async def test_rule_test_disabled_rule(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rule: WorkflowRule,
        db_session: AsyncSession,
    ):
        """Test endpoint returns would_match=0 for a disabled rule."""
        test_rule.is_enabled = False
        db_session.add(test_rule)
        await db_session.commit()

        response = await client.post(
            f"/api/v1/workflows/rules/{test_rule.id}/test",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["would_match"] == 0
        assert data["sample_results"] == []

    @pytest.mark.asyncio
    async def test_rule_test_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test endpoint returns 404 for non-existent rule."""
        response = await client.post("/api/v1/workflows/rules/999999/test", headers=auth_headers)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Executions list tests
# ---------------------------------------------------------------------------


class TestWorkflowExecutions:
    """Tests for GET /workflows/executions."""

    @pytest.mark.asyncio
    async def test_list_executions_requires_auth(self, client: AsyncClient):
        """Executions list returns 401 without auth."""
        response = await client.get("/api/v1/workflows/executions")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_executions_empty(self, client: AsyncClient, auth_headers: dict):
        """Executions list returns empty when no executions exist."""
        response = await client.get("/api/v1/workflows/executions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] == 0


# ---------------------------------------------------------------------------
# Execute rules tests
# ---------------------------------------------------------------------------


class TestWorkflowExecute:
    """Tests for POST /workflows/execute."""

    @pytest.mark.asyncio
    async def test_execute_requires_auth(self, client: AsyncClient):
        """Execute returns 401 without auth."""
        response = await client.post(
            "/api/v1/workflows/execute",
            json={
                "trigger_type": "rfp_created",
                "entity_type": "rfp",
                "entity_id": 1,
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    @patch(
        "app.api.routes.workflows.execute_workflow_rules",
        new_callable=AsyncMock,
    )
    async def test_execute_returns_executions(
        self,
        mock_execute: AsyncMock,
        client: AsyncClient,
        auth_headers: dict,
        test_rule: WorkflowRule,
    ):
        """Execute returns a list of matched executions."""
        mock_execute.return_value = []
        response = await client.post(
            "/api/v1/workflows/execute",
            headers=auth_headers,
            json={
                "trigger_type": "rfp_created",
                "entity_type": "rfp",
                "entity_id": 1,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "executions" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_execute_missing_trigger_type(self, client: AsyncClient, auth_headers: dict):
        """Execute without trigger_type returns 422."""
        response = await client.post(
            "/api/v1/workflows/execute",
            headers=auth_headers,
            json={"entity_type": "rfp", "entity_id": 1},
        )
        assert response.status_code == 422
