"""
Integration tests for rfps/snapshots.py:
  - GET    /rfps/{rfp_id}/snapshots
  - GET    /rfps/{rfp_id}/snapshots/diff
  - GET    /rfps/{rfp_id}/snapshots/amendment-impact
  - POST   /rfps/{rfp_id}/match-score
"""

import hashlib
import json
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.opportunity_snapshot import SAMOpportunitySnapshot
from app.models.rfp import RFP
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password

BASE = "/api/v1/rfps"


def _raw_payload(
    notice_id: str = "NOTICE-001",
    title: str = "Test Opportunity",
    description: str = "Provide cybersecurity services.",
    deadline: str = "2025-06-15",
    naics: str = "541512",
    set_aside: str = "SBA",
    resource_links: list | None = None,
) -> dict:
    return {
        "noticeId": notice_id,
        "solicitationNumber": f"SOL-{notice_id}",
        "title": title,
        "description": description,
        "responseDeadLine": deadline,
        "naicsCode": naics,
        "typeOfSetAside": set_aside,
        "organizationHierarchy": [
            {"name": "Department of Defense"},
            {"name": "U.S. Army"},
        ],
        "resourceLinks": resource_links or [],
        "postedDate": "2025-01-01",
    }


def _raw_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


@pytest_asyncio.fixture
async def owned_rfp(db_session: AsyncSession, test_user: User) -> RFP:
    rfp = RFP(
        user_id=test_user.id,
        title="Snapshot Test RFP",
        solicitation_number="W912HV-24-S-0001",
        notice_id="snap-notice-001",
        agency="Department of Defense",
        status="new",
        posted_date=datetime.utcnow(),
    )
    db_session.add(rfp)
    await db_session.commit()
    await db_session.refresh(rfp)
    return rfp


@pytest_asyncio.fixture
async def two_snapshots(
    db_session: AsyncSession, owned_rfp: RFP, test_user: User
) -> tuple[SAMOpportunitySnapshot, SAMOpportunitySnapshot]:
    payload_old = _raw_payload(
        description="Old description of cybersecurity services.",
        deadline="2025-05-01",
    )
    payload_new = _raw_payload(
        description="Updated description with new scope requirements.",
        deadline="2025-06-15",
    )
    snap_old = SAMOpportunitySnapshot(
        notice_id="snap-notice-001",
        solicitation_number="W912HV-24-S-0001",
        rfp_id=owned_rfp.id,
        user_id=test_user.id,
        fetched_at=datetime.utcnow() - timedelta(days=7),
        posted_date=datetime.utcnow() - timedelta(days=14),
        response_deadline=datetime(2025, 5, 1),
        raw_hash=_raw_hash(payload_old),
        raw_payload=payload_old,
    )
    snap_new = SAMOpportunitySnapshot(
        notice_id="snap-notice-001",
        solicitation_number="W912HV-24-S-0001",
        rfp_id=owned_rfp.id,
        user_id=test_user.id,
        fetched_at=datetime.utcnow(),
        posted_date=datetime.utcnow() - timedelta(days=7),
        response_deadline=datetime(2025, 6, 15),
        raw_hash=_raw_hash(payload_new),
        raw_payload=payload_new,
    )
    db_session.add(snap_old)
    db_session.add(snap_new)
    await db_session.commit()
    await db_session.refresh(snap_old)
    await db_session.refresh(snap_new)
    return snap_old, snap_new


async def _create_other_user(db_session: AsyncSession) -> tuple[User, dict]:
    user = User(
        email="other@example.com",
        hashed_password=hash_password("OtherPass123!"),
        full_name="Other User",
        company_name="Other Co",
        tier="professional",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    tokens = create_token_pair(user.id, user.email, user.tier)
    return user, {"Authorization": f"Bearer {tokens.access_token}"}


class TestListSnapshots:
    """GET /api/v1/rfps/{rfp_id}/snapshots"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient, owned_rfp: RFP):
        response = await client.get(f"{BASE}/{owned_rfp.id}/snapshots")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_snapshots(self, client: AsyncClient, auth_headers: dict, owned_rfp: RFP):
        response = await client.get(f"{BASE}/{owned_rfp.id}/snapshots", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_returns_snapshots(
        self,
        client: AsyncClient,
        auth_headers: dict,
        owned_rfp: RFP,
        two_snapshots: tuple,
    ):
        response = await client.get(f"{BASE}/{owned_rfp.id}/snapshots", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        # Ordered by fetched_at desc — newest first
        assert data[0]["notice_id"] == "snap-notice-001"
        assert "summary" in data[0]
        # raw_payload excluded by default
        assert data[0].get("raw_payload") is None

    @pytest.mark.asyncio
    async def test_include_raw(
        self,
        client: AsyncClient,
        auth_headers: dict,
        owned_rfp: RFP,
        two_snapshots: tuple,
    ):
        response = await client.get(
            f"{BASE}/{owned_rfp.id}/snapshots",
            headers=auth_headers,
            params={"include_raw": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data[0]["raw_payload"] is not None

    @pytest.mark.asyncio
    async def test_rfp_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(f"{BASE}/99999/snapshots", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_idor_isolation(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        owned_rfp: RFP,
        two_snapshots: tuple,
    ):
        _, other_headers = await _create_other_user(db_session)
        response = await client.get(f"{BASE}/{owned_rfp.id}/snapshots", headers=other_headers)
        assert response.status_code == 404


class TestDiffSnapshots:
    """GET /api/v1/rfps/{rfp_id}/snapshots/diff"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient, owned_rfp: RFP):
        response = await client.get(f"{BASE}/{owned_rfp.id}/snapshots/diff")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_diff_auto_latest(
        self,
        client: AsyncClient,
        auth_headers: dict,
        owned_rfp: RFP,
        two_snapshots: tuple,
    ):
        response = await client.get(f"{BASE}/{owned_rfp.id}/snapshots/diff", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "changes" in data
        assert "summary_from" in data
        assert "summary_to" in data
        assert data["from_snapshot_id"] is not None
        assert data["to_snapshot_id"] is not None

    @pytest.mark.asyncio
    async def test_diff_specific_ids(
        self,
        client: AsyncClient,
        auth_headers: dict,
        owned_rfp: RFP,
        two_snapshots: tuple,
    ):
        snap_old, snap_new = two_snapshots
        response = await client.get(
            f"{BASE}/{owned_rfp.id}/snapshots/diff",
            headers=auth_headers,
            params={
                "from_snapshot_id": snap_old.id,
                "to_snapshot_id": snap_new.id,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["from_snapshot_id"] == snap_old.id
        assert data["to_snapshot_id"] == snap_new.id

    @pytest.mark.asyncio
    async def test_diff_not_enough_snapshots(
        self, client: AsyncClient, auth_headers: dict, owned_rfp: RFP
    ):
        response = await client.get(f"{BASE}/{owned_rfp.id}/snapshots/diff", headers=auth_headers)
        assert response.status_code == 404
        assert "Not enough snapshots" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_diff_rfp_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(f"{BASE}/99999/snapshots/diff", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_diff_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        owned_rfp: RFP,
        two_snapshots: tuple,
    ):
        _, other_headers = await _create_other_user(db_session)
        response = await client.get(f"{BASE}/{owned_rfp.id}/snapshots/diff", headers=other_headers)
        assert response.status_code == 404


class TestAmendmentImpact:
    """GET /api/v1/rfps/{rfp_id}/snapshots/amendment-impact"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient, owned_rfp: RFP):
        response = await client.get(f"{BASE}/{owned_rfp.id}/snapshots/amendment-impact")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_amendment_impact_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        owned_rfp: RFP,
        two_snapshots: tuple,
    ):
        response = await client.get(
            f"{BASE}/{owned_rfp.id}/snapshots/amendment-impact",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["rfp_id"] == owned_rfp.id
        assert "amendment_risk_level" in data
        assert data["amendment_risk_level"] in ("low", "medium", "high")
        assert "signals" in data
        assert "impacted_sections" in data
        assert "summary" in data
        assert "approval_workflow" in data

    @pytest.mark.asyncio
    async def test_amendment_impact_not_enough_snapshots(
        self, client: AsyncClient, auth_headers: dict, owned_rfp: RFP
    ):
        response = await client.get(
            f"{BASE}/{owned_rfp.id}/snapshots/amendment-impact",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_amendment_impact_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        owned_rfp: RFP,
        two_snapshots: tuple,
    ):
        _, other_headers = await _create_other_user(db_session)
        response = await client.get(
            f"{BASE}/{owned_rfp.id}/snapshots/amendment-impact",
            headers=other_headers,
        )
        assert response.status_code == 404


class TestMatchScore:
    """POST /api/v1/rfps/{rfp_id}/match-score"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient, owned_rfp: RFP):
        response = await client.post(f"{BASE}/{owned_rfp.id}/match-score")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_match_score_no_profile(
        self, client: AsyncClient, auth_headers: dict, owned_rfp: RFP
    ):
        response = await client.post(f"{BASE}/{owned_rfp.id}/match-score", headers=auth_headers)
        assert response.status_code == 400
        assert "profile" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_match_score_rfp_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(f"{BASE}/99999/match-score", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_match_score_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        owned_rfp: RFP,
    ):
        _, other_headers = await _create_other_user(db_session)
        response = await client.post(f"{BASE}/{owned_rfp.id}/match-score", headers=other_headers)
        assert response.status_code == 404
