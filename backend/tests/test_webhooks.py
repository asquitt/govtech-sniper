"""
RFP Sniper - Webhooks Tests
===========================
Tests for webhook subscriptions and delivery logging.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.webhook import WebhookDelivery
from app.models.user import User


class TestWebhooks:
    @pytest.mark.asyncio
    async def test_webhook_crud_and_delivery(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        # Create webhook subscription
        payload = {
            "name": "RFP Events",
            "target_url": "https://example.com/webhook",
            "event_types": ["rfp.created"],
            "is_active": True,
        }
        response = await client.post(
            "/api/v1/webhooks",
            headers=auth_headers,
            json=payload,
        )
        assert response.status_code == 200
        webhook = response.json()
        webhook_id = webhook["id"]

        # Create RFP to trigger webhook delivery
        rfp_response = await client.post(
            "/api/v1/rfps",
            params={"user_id": test_user.id},
            json={
                "title": "Webhook Test RFP",
                "solicitation_number": "WH-001",
                "notice_id": "wh-notice-001",
                "agency": "Test Agency",
                "rfp_type": "solicitation",
            },
        )
        assert rfp_response.status_code == 200

        deliveries_result = await db_session.execute(
            select(WebhookDelivery).where(WebhookDelivery.subscription_id == webhook_id)
        )
        deliveries = deliveries_result.scalars().all()
        assert len(deliveries) == 1
        assert deliveries[0].event_type == "rfp.created"

        # List deliveries via API
        response = await client.get(
            f"/api/v1/webhooks/{webhook_id}/deliveries",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert len(response.json()) == 1

        # Update webhook
        response = await client.patch(
            f"/api/v1/webhooks/{webhook_id}",
            headers=auth_headers,
            json={"is_active": False},
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is False

        # Delete webhook
        response = await client.delete(
            f"/api/v1/webhooks/{webhook_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
