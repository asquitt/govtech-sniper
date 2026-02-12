"""Integration tests for template marketplace depth, report builder sharing, and support APIs."""

from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password


async def _create_user(
    session: AsyncSession,
    email: str,
    full_name: str,
) -> User:
    user = User(
        email=email,
        hashed_password=hash_password("TestPassword123!"),
        full_name=full_name,
        company_name="Integration Corp",
        tier="professional",
        is_active=True,
        is_verified=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


class TestTemplateMarketplaceDepth:
    @pytest.mark.asyncio
    async def test_vertical_templates_seed_and_marketplace_discovery(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        templates = await client.get("/api/v1/templates", headers=auth_headers)
        assert templates.status_code == 200
        payload = templates.json()

        assert any(
            item["category"] == "Proposal Structure" and item["subcategory"] == "IT Services"
            for item in payload
        )
        assert any(
            item["category"] == "Compliance Matrix" and item["subcategory"] == "GSA MAS"
            for item in payload
        )

        marketplace = await client.get(
            "/api/v1/templates/marketplace",
            headers=auth_headers,
            params={"category": "Proposal Structure"},
        )
        assert marketplace.status_code == 200
        assert marketplace.json()["total"] >= 3

    @pytest.mark.asyncio
    async def test_publish_rate_and_fork_template(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        create_template = await client.post(
            "/api/v1/templates",
            headers=auth_headers,
            json={
                "name": "Community Capture Plan",
                "category": "Technical",
                "description": "Template for capture planning",
                "template_text": "Capture strategy for {agency}",
                "placeholders": {"agency": "Agency name"},
                "keywords": ["community", "capture"],
            },
        )
        assert create_template.status_code == 200
        template_id = create_template.json()["id"]

        publish = await client.post(
            f"/api/v1/templates/{template_id}/publish", headers=auth_headers
        )
        assert publish.status_code == 200
        assert publish.json()["is_public"] is True

        rate = await client.post(
            f"/api/v1/templates/{template_id}/rate",
            headers=auth_headers,
            json={"rating": 5},
        )
        assert rate.status_code == 200
        assert rate.json()["average_rating"] == 5.0

        fork = await client.post(f"/api/v1/templates/{template_id}/fork", headers=auth_headers)
        assert fork.status_code == 200
        assert fork.json()["forked_from_id"] == template_id


class TestDynamicReportsAndSupport:
    @pytest.mark.asyncio
    async def test_reports_shared_views_and_scheduled_delivery(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        teammate = await _create_user(db_session, "teammate@example.com", "Teammate User")
        teammate_tokens = create_token_pair(teammate.id, teammate.email, teammate.tier)
        teammate_headers = {"Authorization": f"Bearer {teammate_tokens.access_token}"}

        create_report = await client.post(
            "/api/v1/reports",
            headers=auth_headers,
            json={
                "name": "Shared Pipeline View",
                "report_type": "pipeline",
                "config": {
                    "columns": ["opportunity", "agency", "value"],
                    "filters": {},
                    "group_by": None,
                    "sort_by": None,
                    "sort_order": "asc",
                },
                "is_shared": True,
                "shared_with_emails": ["teammate@example.com"],
            },
        )
        assert create_report.status_code == 200
        report = create_report.json()
        report_id = report["id"]

        teammate_list = await client.get("/api/v1/reports", headers=teammate_headers)
        assert teammate_list.status_code == 200
        assert any(item["id"] == report_id for item in teammate_list.json())

        generated = await client.post(f"/api/v1/reports/{report_id}/generate", headers=auth_headers)
        assert generated.status_code == 200
        assert generated.json()["columns"] == ["opportunity", "agency", "value"]

        schedule = await client.post(
            f"/api/v1/reports/{report_id}/schedule",
            headers=auth_headers,
            json={
                "frequency": "weekly",
                "recipients": ["ops@example.com", "exec@example.com"],
                "enabled": True,
                "subject": "Weekly Pipeline Snapshot",
            },
        )
        assert schedule.status_code == 200
        assert schedule.json()["delivery_enabled"] is True
        assert schedule.json()["delivery_recipients"] == ["ops@example.com", "exec@example.com"]

        send_now = await client.post(
            f"/api/v1/reports/{report_id}/delivery/send",
            headers=auth_headers,
        )
        assert send_now.status_code == 200
        payload = send_now.json()
        assert payload["status"] == "sent"
        assert payload["recipient_count"] == 2
        datetime.fromisoformat(payload["delivered_at"])

    @pytest.mark.asyncio
    async def test_support_help_center_tutorials_and_chat(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        articles = await client.get(
            "/api/v1/support/help-center/articles",
            headers=auth_headers,
            params={"q": "report"},
        )
        assert articles.status_code == 200
        assert any("report" in item["title"].lower() for item in articles.json())

        tutorials = await client.get("/api/v1/support/tutorials", headers=auth_headers)
        assert tutorials.status_code == 200
        assert len(tutorials.json()) >= 3

        chat = await client.post(
            "/api/v1/support/chat",
            headers=auth_headers,
            json={"message": "How do I share report views?", "current_route": "/reports"},
        )
        assert chat.status_code == 200
        chat_payload = chat.json()
        assert "report" in chat_payload["reply"].lower()
        assert "report-builder-guide" in chat_payload["suggested_article_ids"]
        assert chat_payload["suggested_tutorial_id"] == "tutorial-reports"
