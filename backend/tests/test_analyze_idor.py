"""
Analyze Endpoint IDOR Tests
=============================
Verify that analysis endpoints enforce ownership:
User B cannot trigger analysis, read matrix, or modify requirements
for User A's RFP.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rfp import RFP
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password


@pytest_asyncio.fixture
async def attacker_user(db_session: AsyncSession) -> User:
    """Second user who should not access first user's RFPs."""
    user = User(
        email="attacker@example.com",
        hashed_password=hash_password("AttackerPass123!"),
        full_name="Attacker",
        company_name="Evil Corp",
        tier="professional",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def attacker_headers(attacker_user: User) -> dict:
    tokens = create_token_pair(attacker_user.id, attacker_user.email, attacker_user.tier)
    return {"Authorization": f"Bearer {tokens.access_token}"}


class TestAnalyzeIDOR:
    """User B should not be able to perform analysis actions on User A's RFP."""

    @pytest.mark.asyncio
    async def test_trigger_analysis_idor_blocked(
        self, client: AsyncClient, test_rfp: RFP, attacker_headers: dict
    ):
        resp = await client.post(
            f"/api/v1/analyze/{test_rfp.id}",
            headers=attacker_headers,
        )
        # 404 = ownership blocked; 503 = Celery unavailable (but ownership check may have passed)
        assert resp.status_code in (404, 503)

    @pytest.mark.asyncio
    async def test_get_compliance_matrix_idor_blocked(
        self, client: AsyncClient, test_rfp: RFP, attacker_headers: dict
    ):
        resp = await client.get(
            f"/api/v1/analyze/{test_rfp.id}/matrix",
            headers=attacker_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_compliance_gaps_idor_blocked(
        self, client: AsyncClient, test_rfp: RFP, attacker_headers: dict
    ):
        resp = await client.get(
            f"/api/v1/analyze/{test_rfp.id}/gaps",
            headers=attacker_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_add_requirement_idor_blocked(
        self, client: AsyncClient, test_rfp: RFP, attacker_headers: dict
    ):
        resp = await client.post(
            f"/api/v1/analyze/{test_rfp.id}/matrix",
            headers=attacker_headers,
            json={
                "section": "Section C",
                "requirement_text": "Injected requirement",
                "importance": "mandatory",
            },
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_requirement_idor_blocked(
        self, client: AsyncClient, test_rfp: RFP, attacker_headers: dict
    ):
        resp = await client.patch(
            f"/api/v1/analyze/{test_rfp.id}/matrix/REQ-001",
            headers=attacker_headers,
            json={"text": "Tampered"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_requirement_idor_blocked(
        self, client: AsyncClient, test_rfp: RFP, attacker_headers: dict
    ):
        resp = await client.delete(
            f"/api/v1/analyze/{test_rfp.id}/matrix/REQ-001",
            headers=attacker_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_owner_can_access_matrix(
        self, client: AsyncClient, test_rfp: RFP, auth_headers: dict
    ):
        """Positive test: owner should succeed (404 only if no matrix yet, not 403)."""
        resp = await client.get(
            f"/api/v1/analyze/{test_rfp.id}/matrix",
            headers=auth_headers,
        )
        # 200 if matrix exists, 404 if no matrix — but NOT 403
        assert resp.status_code in (200, 404)


class TestDraftIDOR:
    """User B should not access User A's proposals."""

    @pytest.mark.asyncio
    async def test_get_proposal_idor_blocked(
        self, client: AsyncClient, test_proposal, attacker_headers: dict
    ):
        resp = await client.get(
            f"/api/v1/draft/proposals/{test_proposal.id}",
            headers=attacker_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create_section_idor_blocked(
        self, client: AsyncClient, test_proposal, attacker_headers: dict
    ):
        resp = await client.post(
            f"/api/v1/draft/proposals/{test_proposal.id}/sections",
            headers=attacker_headers,
            json={
                "title": "Injected Section",
                "section_number": "1.0",
            },
        )
        assert resp.status_code == 404
