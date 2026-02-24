"""
Tests for teaming_board/requests routes - Teaming requests, trends, digest, audit export.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capture import (
    TeamingDigestChannel,
    TeamingDigestFrequency,
    TeamingDigestSchedule,
    TeamingPartner,
)
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password

BASE = "/api/v1/teaming"


@pytest_asyncio.fixture
async def partner_a(db_session: AsyncSession, test_user: User) -> TeamingPartner:
    p = TeamingPartner(
        user_id=test_user.id,
        name="Partner Alpha",
        is_public=True,
        naics_codes=["541512"],
        set_asides=["8a"],
    )
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


@pytest_asyncio.fixture
async def user2_and_headers(
    db_session: AsyncSession,
) -> tuple[User, dict]:
    user2 = User(
        email="sender@example.com",
        hashed_password=hash_password("Password123!"),
        full_name="Sender User",
        company_name="Sender Co",
        tier="professional",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user2)
    await db_session.commit()
    await db_session.refresh(user2)
    tokens = create_token_pair(user2.id, user2.email, user2.tier)
    return user2, {"Authorization": f"Bearer {tokens.access_token}"}


# ============================================================================
# POST /requests - send teaming request
# ============================================================================


class TestSendTeamingRequestAuth:
    @pytest.mark.asyncio
    async def test_send_request_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.post(f"{BASE}/requests", json={"to_partner_id": 1})
        assert resp.status_code == 401


class TestSendTeamingRequest:
    @pytest.mark.asyncio
    async def test_send_request_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        partner_a: TeamingPartner,
    ) -> None:
        resp = await client.post(
            f"{BASE}/requests",
            headers=auth_headers,
            json={"to_partner_id": partner_a.id, "message": "Let's team up!"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["to_partner_id"] == partner_a.id
        assert data["status"] == "pending"
        assert data["message"] == "Let's team up!"
        assert data["partner_name"] == "Partner Alpha"

    @pytest.mark.asyncio
    async def test_send_request_to_nonexistent_partner_404(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.post(
            f"{BASE}/requests",
            headers=auth_headers,
            json={"to_partner_id": 99999},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_send_request_to_private_partner_404(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        private = TeamingPartner(user_id=test_user.id, name="Private", is_public=False)
        db_session.add(private)
        await db_session.commit()
        await db_session.refresh(private)

        resp = await client.post(
            f"{BASE}/requests",
            headers=auth_headers,
            json={"to_partner_id": private.id},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_send_duplicate_pending_request_409(
        self,
        client: AsyncClient,
        auth_headers: dict,
        partner_a: TeamingPartner,
    ) -> None:
        # First request
        await client.post(
            f"{BASE}/requests",
            headers=auth_headers,
            json={"to_partner_id": partner_a.id},
        )
        # Duplicate
        resp = await client.post(
            f"{BASE}/requests",
            headers=auth_headers,
            json={"to_partner_id": partner_a.id},
        )
        assert resp.status_code == 409


# ============================================================================
# GET /requests - list sent/received requests
# ============================================================================


class TestListTeamingRequests:
    @pytest.mark.asyncio
    async def test_list_requests_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get(f"{BASE}/requests")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_list_sent_requests(
        self,
        client: AsyncClient,
        auth_headers: dict,
        partner_a: TeamingPartner,
    ) -> None:
        await client.post(
            f"{BASE}/requests",
            headers=auth_headers,
            json={"to_partner_id": partner_a.id},
        )
        resp = await client.get(
            f"{BASE}/requests",
            headers=auth_headers,
            params={"direction": "sent"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["partner_name"] == "Partner Alpha"

    @pytest.mark.asyncio
    async def test_list_received_requests(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
        partner_a: TeamingPartner,
        user2_and_headers: tuple[User, dict],
    ) -> None:
        """User2 sends a request to partner_a (owned by test_user).
        test_user should see it as received."""
        user2, headers2 = user2_and_headers
        await client.post(
            f"{BASE}/requests",
            headers=headers2,
            json={"to_partner_id": partner_a.id, "message": "Hello from user2"},
        )
        resp = await client.get(
            f"{BASE}/requests",
            headers=auth_headers,
            params={"direction": "received"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["from_user_name"] == "Sender User"

    @pytest.mark.asyncio
    async def test_list_received_no_partner_returns_empty(
        self,
        client: AsyncClient,
        user2_and_headers: tuple[User, dict],
    ) -> None:
        """User2 has no partner profiles, so received list is empty."""
        _, headers2 = user2_and_headers
        resp = await client.get(
            f"{BASE}/requests",
            headers=headers2,
            params={"direction": "received"},
        )
        assert resp.status_code == 200
        assert resp.json() == []


# ============================================================================
# PATCH /requests/{request_id} - accept/decline
# ============================================================================


class TestUpdateTeamingRequest:
    @pytest.mark.asyncio
    async def test_update_request_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.patch(f"{BASE}/requests/1", json={"status": "accepted"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_accept_request(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
        partner_a: TeamingPartner,
        user2_and_headers: tuple[User, dict],
    ) -> None:
        user2, headers2 = user2_and_headers
        # User2 sends request to partner_a
        send_resp = await client.post(
            f"{BASE}/requests",
            headers=headers2,
            json={"to_partner_id": partner_a.id},
        )
        request_id = send_resp.json()["id"]

        # test_user (owner of partner_a) accepts
        resp = await client.patch(
            f"{BASE}/requests/{request_id}",
            headers=auth_headers,
            json={"status": "accepted"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "accepted"

    @pytest.mark.asyncio
    async def test_decline_request(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        partner_a: TeamingPartner,
        user2_and_headers: tuple[User, dict],
    ) -> None:
        user2, headers2 = user2_and_headers
        send_resp = await client.post(
            f"{BASE}/requests",
            headers=headers2,
            json={"to_partner_id": partner_a.id},
        )
        request_id = send_resp.json()["id"]

        resp = await client.patch(
            f"{BASE}/requests/{request_id}",
            headers=auth_headers,
            json={"status": "declined"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "declined"

    @pytest.mark.asyncio
    async def test_invalid_status_400(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        partner_a: TeamingPartner,
        user2_and_headers: tuple[User, dict],
    ) -> None:
        user2, headers2 = user2_and_headers
        send_resp = await client.post(
            f"{BASE}/requests",
            headers=headers2,
            json={"to_partner_id": partner_a.id},
        )
        request_id = send_resp.json()["id"]

        resp = await client.patch(
            f"{BASE}/requests/{request_id}",
            headers=auth_headers,
            json={"status": "invalid_status"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_update_nonexistent_request_404(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.patch(
            f"{BASE}/requests/99999",
            headers=auth_headers,
            json={"status": "accepted"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_request_non_owner_403(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        partner_a: TeamingPartner,
        user2_and_headers: tuple[User, dict],
    ) -> None:
        """The sender (user2) should not be able to accept their own request."""
        user2, headers2 = user2_and_headers
        send_resp = await client.post(
            f"{BASE}/requests",
            headers=headers2,
            json={"to_partner_id": partner_a.id},
        )
        request_id = send_resp.json()["id"]

        # user2 tries to accept (they don't own the partner)
        resp = await client.patch(
            f"{BASE}/requests/{request_id}",
            headers=headers2,
            json={"status": "accepted"},
        )
        assert resp.status_code == 403


# ============================================================================
# GET /requests/fit-trends
# ============================================================================


class TestFitTrends:
    @pytest.mark.asyncio
    async def test_fit_trends_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get(f"{BASE}/requests/fit-trends")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_fit_trends_empty(self, client: AsyncClient, auth_headers: dict) -> None:
        resp = await client.get(
            f"{BASE}/requests/fit-trends",
            headers=auth_headers,
            params={"days": 7},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["days"] == 7
        assert data["total_sent"] == 0
        assert data["acceptance_rate"] == 0.0
        assert len(data["points"]) == 7

    @pytest.mark.asyncio
    async def test_fit_trends_with_data(
        self,
        client: AsyncClient,
        auth_headers: dict,
        partner_a: TeamingPartner,
    ) -> None:
        # Create a request so trends have data
        await client.post(
            f"{BASE}/requests",
            headers=auth_headers,
            json={"to_partner_id": partner_a.id},
        )
        resp = await client.get(
            f"{BASE}/requests/fit-trends",
            headers=auth_headers,
            params={"days": 30},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_sent"] == 1
        assert data["pending_count"] == 1


# ============================================================================
# GET /requests/partner-trends
# ============================================================================


class TestPartnerTrends:
    @pytest.mark.asyncio
    async def test_partner_trends_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get(f"{BASE}/requests/partner-trends")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_partner_trends_empty(self, client: AsyncClient, auth_headers: dict) -> None:
        resp = await client.get(
            f"{BASE}/requests/partner-trends",
            headers=auth_headers,
            params={"days": 30},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["days"] == 30
        assert data["partners"] == []

    @pytest.mark.asyncio
    async def test_partner_trends_with_data(
        self,
        client: AsyncClient,
        auth_headers: dict,
        partner_a: TeamingPartner,
    ) -> None:
        await client.post(
            f"{BASE}/requests",
            headers=auth_headers,
            json={"to_partner_id": partner_a.id},
        )
        resp = await client.get(
            f"{BASE}/requests/partner-trends",
            headers=auth_headers,
            params={"days": 30},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["partners"]) == 1
        assert data["partners"][0]["partner_name"] == "Partner Alpha"
        assert data["partners"][0]["sent_count"] == 1


# ============================================================================
# GET /requests/partner-cohorts
# ============================================================================


class TestPartnerCohorts:
    @pytest.mark.asyncio
    async def test_partner_cohorts_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get(f"{BASE}/requests/partner-cohorts")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_partner_cohorts_empty(self, client: AsyncClient, auth_headers: dict) -> None:
        resp = await client.get(
            f"{BASE}/requests/partner-cohorts",
            headers=auth_headers,
            params={"days": 30},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_sent"] == 0
        assert data["naics_cohorts"] == []
        assert data["set_aside_cohorts"] == []

    @pytest.mark.asyncio
    async def test_partner_cohorts_with_data(
        self,
        client: AsyncClient,
        auth_headers: dict,
        partner_a: TeamingPartner,
    ) -> None:
        await client.post(
            f"{BASE}/requests",
            headers=auth_headers,
            json={"to_partner_id": partner_a.id},
        )
        resp = await client.get(
            f"{BASE}/requests/partner-cohorts",
            headers=auth_headers,
            params={"days": 30, "top_n": 5},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_sent"] == 1
        # Partner Alpha has naics_codes=["541512"] and set_asides=["8a"]
        assert len(data["naics_cohorts"]) >= 1
        assert len(data["set_aside_cohorts"]) >= 1


# ============================================================================
# GET /digest-schedule & PATCH /digest-schedule
# ============================================================================


class TestDigestSchedule:
    @pytest.mark.asyncio
    async def test_get_digest_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get(f"{BASE}/digest-schedule")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_get_digest_creates_default(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.get(f"{BASE}/digest-schedule", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["frequency"] == "weekly"
        assert data["day_of_week"] == 1
        assert data["hour_utc"] == 14
        assert data["minute_utc"] == 0
        assert data["channel"] == "in_app"
        assert data["is_enabled"] is True

    @pytest.mark.asyncio
    async def test_get_digest_idempotent(self, client: AsyncClient, auth_headers: dict) -> None:
        """Calling GET twice returns the same schedule (no duplicate creation)."""
        resp1 = await client.get(f"{BASE}/digest-schedule", headers=auth_headers)
        resp2 = await client.get(f"{BASE}/digest-schedule", headers=auth_headers)
        assert resp1.json() == resp2.json()

    @pytest.mark.asyncio
    async def test_update_digest_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.patch(
            f"{BASE}/digest-schedule",
            json={"frequency": "daily", "hour_utc": 9, "minute_utc": 0},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_update_digest_schedule(self, client: AsyncClient, auth_headers: dict) -> None:
        resp = await client.patch(
            f"{BASE}/digest-schedule",
            headers=auth_headers,
            json={
                "frequency": "daily",
                "day_of_week": None,
                "hour_utc": 8,
                "minute_utc": 30,
                "channel": "email",
                "include_declined_reasons": False,
                "is_enabled": True,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["frequency"] == "daily"
        assert data["hour_utc"] == 8
        assert data["minute_utc"] == 30
        assert data["channel"] == "email"
        assert data["include_declined_reasons"] is False

    @pytest.mark.asyncio
    async def test_update_digest_invalid_day_of_week(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.patch(
            f"{BASE}/digest-schedule",
            headers=auth_headers,
            json={
                "frequency": "weekly",
                "day_of_week": 7,
                "hour_utc": 14,
                "minute_utc": 0,
                "channel": "in_app",
                "include_declined_reasons": True,
                "is_enabled": True,
            },
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_update_digest_invalid_hour(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.patch(
            f"{BASE}/digest-schedule",
            headers=auth_headers,
            json={
                "frequency": "weekly",
                "day_of_week": 1,
                "hour_utc": 25,
                "minute_utc": 0,
                "channel": "in_app",
                "include_declined_reasons": True,
                "is_enabled": True,
            },
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_update_digest_invalid_minute(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.patch(
            f"{BASE}/digest-schedule",
            headers=auth_headers,
            json={
                "frequency": "weekly",
                "day_of_week": 1,
                "hour_utc": 14,
                "minute_utc": 60,
                "channel": "in_app",
                "include_declined_reasons": True,
                "is_enabled": True,
            },
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_update_digest_invalid_frequency(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.patch(
            f"{BASE}/digest-schedule",
            headers=auth_headers,
            json={
                "frequency": "monthly",
                "day_of_week": 1,
                "hour_utc": 14,
                "minute_utc": 0,
                "channel": "in_app",
                "include_declined_reasons": True,
                "is_enabled": True,
            },
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_update_digest_invalid_channel(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.patch(
            f"{BASE}/digest-schedule",
            headers=auth_headers,
            json={
                "frequency": "weekly",
                "day_of_week": 1,
                "hour_utc": 14,
                "minute_utc": 0,
                "channel": "sms",
                "include_declined_reasons": True,
                "is_enabled": True,
            },
        )
        assert resp.status_code == 400


# ============================================================================
# POST /digest-send
# ============================================================================


class TestDigestSend:
    @pytest.mark.asyncio
    async def test_digest_send_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.post(f"{BASE}/digest-send")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_digest_send_success(self, client: AsyncClient, auth_headers: dict) -> None:
        resp = await client.post(
            f"{BASE}/digest-send",
            headers=auth_headers,
            params={"days": 7},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "generated_at" in data
        assert data["period_days"] == 7
        assert "summary" in data
        assert "schedule" in data

    @pytest.mark.asyncio
    async def test_digest_send_disabled_400(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """If digest is disabled, sending should fail with 400."""
        schedule = TeamingDigestSchedule(
            user_id=test_user.id,
            frequency=TeamingDigestFrequency.WEEKLY,
            channel=TeamingDigestChannel.IN_APP,
            is_enabled=False,
        )
        db_session.add(schedule)
        await db_session.commit()

        resp = await client.post(
            f"{BASE}/digest-send",
            headers=auth_headers,
            params={"days": 30},
        )
        assert resp.status_code == 400


# ============================================================================
# GET /requests/audit-export
# ============================================================================


class TestAuditExport:
    @pytest.mark.asyncio
    async def test_audit_export_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get(f"{BASE}/requests/audit-export")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_audit_export_csv_empty(self, client: AsyncClient, auth_headers: dict) -> None:
        resp = await client.get(
            f"{BASE}/requests/audit-export",
            headers=auth_headers,
            params={"direction": "all", "days": 30},
        )
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        # CSV header row should still be present
        lines = resp.text.strip().split("\n")
        assert len(lines) >= 1  # at least the header
        assert "request_id" in lines[0]

    @pytest.mark.asyncio
    async def test_audit_export_csv_with_data(
        self,
        client: AsyncClient,
        auth_headers: dict,
        partner_a: TeamingPartner,
    ) -> None:
        await client.post(
            f"{BASE}/requests",
            headers=auth_headers,
            json={"to_partner_id": partner_a.id, "message": "Audit test"},
        )
        resp = await client.get(
            f"{BASE}/requests/audit-export",
            headers=auth_headers,
            params={"direction": "sent", "days": 30},
        )
        assert resp.status_code == 200
        lines = resp.text.strip().split("\n")
        assert len(lines) >= 2  # header + at least 1 data row
        assert "request_sent" in resp.text

    @pytest.mark.asyncio
    async def test_audit_export_direction_received(
        self,
        client: AsyncClient,
        auth_headers: dict,
        partner_a: TeamingPartner,
        user2_and_headers: tuple[User, dict],
    ) -> None:
        user2, headers2 = user2_and_headers
        await client.post(
            f"{BASE}/requests",
            headers=headers2,
            json={"to_partner_id": partner_a.id},
        )
        resp = await client.get(
            f"{BASE}/requests/audit-export",
            headers=auth_headers,
            params={"direction": "received", "days": 30},
        )
        assert resp.status_code == 200
        lines = resp.text.strip().split("\n")
        assert len(lines) >= 2

    @pytest.mark.asyncio
    async def test_audit_export_content_disposition(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ) -> None:
        resp = await client.get(
            f"{BASE}/requests/audit-export",
            headers=auth_headers,
            params={"direction": "all", "days": 30},
        )
        assert resp.status_code == 200
        assert "attachment" in resp.headers.get("content-disposition", "")
        assert "teaming_requests_audit_" in resp.headers.get("content-disposition", "")
