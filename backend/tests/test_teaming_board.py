"""
RFP Sniper - Teaming Board Tests
================================
Integration coverage for public partner discovery and request workflows.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rfp import RFP
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password


async def _create_user_and_headers(
    db_session: AsyncSession,
    email: str,
    full_name: str,
) -> tuple[User, dict[str, str]]:
    user = User(
        email=email,
        hashed_password=hash_password("TestPassword123!"),
        full_name=full_name,
        company_name="Test Company",
        tier="professional",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    tokens = create_token_pair(user.id, user.email, str(user.tier))
    return user, {"Authorization": f"Bearer {tokens.access_token}"}


class TestTeamingBoard:
    @pytest.mark.asyncio
    async def test_public_partner_search_and_request_lifecycle(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
    ):
        create_partner = await client.post(
            "/api/v1/capture/partners",
            headers=auth_headers,
            json={"name": "Public Partner Co", "partner_type": "sub"},
        )
        assert create_partner.status_code == 200
        partner_id = create_partner.json()["id"]

        make_public = await client.patch(
            f"/api/v1/teaming/my-profile/{partner_id}",
            headers=auth_headers,
            params={"is_public": True},
        )
        assert make_public.status_code == 200
        assert make_public.json()["is_public"] is True

        search = await client.get(
            "/api/v1/teaming/search",
            headers=auth_headers,
            params={"q": "Public Partner"},
        )
        assert search.status_code == 200
        assert any(item["id"] == partner_id for item in search.json())

        send_request = await client.post(
            "/api/v1/teaming/requests",
            headers=auth_headers,
            json={
                "to_partner_id": partner_id,
                "rfp_id": test_rfp.id,
                "message": "Interested in teaming",
            },
        )
        assert send_request.status_code == 200
        request = send_request.json()
        assert request["status"] == "pending"

        sent = await client.get(
            "/api/v1/teaming/requests",
            headers=auth_headers,
            params={"direction": "sent"},
        )
        assert sent.status_code == 200
        assert any(item["id"] == request["id"] for item in sent.json())

        update = await client.patch(
            f"/api/v1/teaming/requests/{request['id']}",
            headers=auth_headers,
            json={"status": "accepted"},
        )
        assert update.status_code == 200
        assert update.json()["status"] == "accepted"

        nda = await client.post(
            "/api/v1/teaming/ndas",
            headers=auth_headers,
            json={
                "partner_id": partner_id,
                "rfp_id": test_rfp.id,
                "notes": "Draft NDA",
            },
        )
        assert nda.status_code == 201
        assert nda.json()["partner_id"] == partner_id

        rating = await client.post(
            "/api/v1/teaming/ratings",
            headers=auth_headers,
            json={
                "partner_id": partner_id,
                "rfp_id": test_rfp.id,
                "rating": 4,
                "comment": "Good responsiveness",
            },
        )
        assert rating.status_code == 201
        assert rating.json()["partner_id"] == partner_id

    @pytest.mark.asyncio
    async def test_multi_user_received_request_acceptance_and_gap_analysis(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_rfp: RFP,
    ):
        _, receiver_headers = await _create_user_and_headers(
            db_session,
            email="receiver-partner@example.com",
            full_name="Receiver Partner",
        )

        create_receiver_partner = await client.post(
            "/api/v1/capture/partners",
            headers=receiver_headers,
            json={"name": "Receiver Public Partner", "partner_type": "sub"},
        )
        assert create_receiver_partner.status_code == 200
        receiver_partner_id = create_receiver_partner.json()["id"]

        make_receiver_partner_public = await client.patch(
            f"/api/v1/teaming/my-profile/{receiver_partner_id}",
            headers=receiver_headers,
            params={"is_public": True},
        )
        assert make_receiver_partner_public.status_code == 200
        assert make_receiver_partner_public.json()["is_public"] is True

        sender_request = await client.post(
            "/api/v1/teaming/requests",
            headers=auth_headers,
            json={
                "to_partner_id": receiver_partner_id,
                "rfp_id": test_rfp.id,
                "message": "Need teaming support",
            },
        )
        assert sender_request.status_code == 200
        request_id = sender_request.json()["id"]
        assert sender_request.json()["status"] == "pending"

        receiver_inbox = await client.get(
            "/api/v1/teaming/requests",
            headers=receiver_headers,
            params={"direction": "received"},
        )
        assert receiver_inbox.status_code == 200
        inbox_item = next(item for item in receiver_inbox.json() if item["id"] == request_id)
        assert inbox_item["status"] == "pending"
        assert inbox_item["from_user_name"] is not None
        assert inbox_item["from_user_email"] is not None

        accept = await client.patch(
            f"/api/v1/teaming/requests/{request_id}",
            headers=receiver_headers,
            json={"status": "accepted"},
        )
        assert accept.status_code == 200
        assert accept.json()["status"] == "accepted"

        sender_sent = await client.get(
            "/api/v1/teaming/requests",
            headers=auth_headers,
            params={"direction": "sent"},
        )
        assert sender_sent.status_code == 200
        sent_item = next(item for item in sender_sent.json() if item["id"] == request_id)
        assert sent_item["status"] == "accepted"
        assert sent_item["from_user_email"] is not None

        gap_analysis = await client.get(
            f"/api/v1/teaming/gap-analysis/{test_rfp.id}",
            headers=auth_headers,
        )
        assert gap_analysis.status_code == 200
        gap_payload = gap_analysis.json()
        assert gap_payload["rfp_id"] == test_rfp.id
        assert isinstance(gap_payload["gaps"], list)
        assert isinstance(gap_payload["recommended_partners"], list)

        fit_trends = await client.get(
            "/api/v1/teaming/requests/fit-trends",
            headers=auth_headers,
            params={"days": 30},
        )
        assert fit_trends.status_code == 200
        fit_payload = fit_trends.json()
        assert fit_payload["days"] == 30
        assert fit_payload["total_sent"] >= 1
        assert fit_payload["accepted_count"] >= 1
        assert len(fit_payload["points"]) == 30

        partner_trends = await client.get(
            "/api/v1/teaming/requests/partner-trends",
            headers=auth_headers,
            params={"days": 30},
        )
        assert partner_trends.status_code == 200
        partner_trends_payload = partner_trends.json()
        assert partner_trends_payload["days"] == 30
        assert len(partner_trends_payload["partners"]) >= 1

        digest_schedule = await client.get(
            "/api/v1/teaming/digest-schedule",
            headers=auth_headers,
        )
        assert digest_schedule.status_code == 200
        assert digest_schedule.json()["frequency"] == "weekly"

        update_digest_schedule = await client.patch(
            "/api/v1/teaming/digest-schedule",
            headers=auth_headers,
            json={
                "frequency": "weekly",
                "day_of_week": 3,
                "hour_utc": 16,
                "minute_utc": 15,
                "channel": "in_app",
                "include_declined_reasons": False,
                "is_enabled": True,
            },
        )
        assert update_digest_schedule.status_code == 200
        assert update_digest_schedule.json()["include_declined_reasons"] is False

        digest_send = await client.post(
            "/api/v1/teaming/digest-send",
            headers=auth_headers,
            params={"days": 30},
        )
        assert digest_send.status_code == 200
        digest_payload = digest_send.json()
        assert digest_payload["period_days"] == 30
        assert digest_payload["schedule"]["last_sent_at"] is not None
        assert isinstance(digest_payload["top_partners"], list)
        if digest_payload["top_partners"]:
            assert "declined_count" not in digest_payload["top_partners"][0]

        audit_export = await client.get(
            "/api/v1/teaming/requests/audit-export",
            headers=auth_headers,
            params={"direction": "all", "days": 30},
        )
        assert audit_export.status_code == 200
        assert "text/csv" in audit_export.headers["content-type"]
        assert audit_export.headers.get("content-disposition")
        assert "request_id,event_type,event_timestamp" in audit_export.text
        assert str(request_id) in audit_export.text
        assert "request_accepted" in audit_export.text
