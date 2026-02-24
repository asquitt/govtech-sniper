"""
Tests for teaming_board/gap_analysis routes - AI-powered capability gap analysis.

Since this endpoint calls an AI service (Gemini), tests focus on auth,
validation, and mock-based response structure rather than AI output quality.
"""

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capture import TeamingPartner
from app.models.rfp import RFP
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password
from app.services.capability_gap_service import CapabilityGapResult

BASE = "/api/v1/teaming"


@pytest_asyncio.fixture
async def rfp_for_gap(db_session: AsyncSession, test_user: User) -> RFP:
    from datetime import datetime

    rfp = RFP(
        user_id=test_user.id,
        title="Cloud Migration Services",
        solicitation_number="FA8773-25-R-0001",
        notice_id="gap-notice-1",
        agency="Department of the Air Force",
        naics_code="541512",
        status="new",
        posted_date=datetime.utcnow(),
    )
    db_session.add(rfp)
    await db_session.commit()
    await db_session.refresh(rfp)
    return rfp


@pytest_asyncio.fixture
async def public_partner_for_gap(db_session: AsyncSession, test_user: User) -> TeamingPartner:
    partner = TeamingPartner(
        user_id=test_user.id,
        name="Gap Analysis Partner",
        is_public=True,
        capabilities=["AWS Migration"],
        naics_codes=["541512"],
    )
    db_session.add(partner)
    await db_session.commit()
    await db_session.refresh(partner)
    return partner


class TestGapAnalysisAuth:
    @pytest.mark.asyncio
    async def test_gap_analysis_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get(f"{BASE}/gap-analysis/1")
        assert resp.status_code == 401


class TestGapAnalysis:
    @pytest.mark.asyncio
    async def test_gap_analysis_rfp_not_found(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """When the RFP does not exist, the service raises ValueError.
        The ASGI test transport propagates the exception rather than returning 500."""
        with pytest.raises(ValueError, match="RFP 99999 not found"):
            await client.get(f"{BASE}/gap-analysis/99999", headers=auth_headers)

    @pytest.mark.asyncio
    async def test_gap_analysis_success_mock(
        self,
        client: AsyncClient,
        auth_headers: dict,
        rfp_for_gap: RFP,
        public_partner_for_gap: TeamingPartner,
    ) -> None:
        """Test gap analysis with mocked service to avoid Gemini calls."""
        mock_result = CapabilityGapResult(
            rfp_id=rfp_for_gap.id,
            gaps=[
                {
                    "gap_type": "technical",
                    "description": "Cloud migration expertise needed",
                    "required_value": "AWS/Azure",
                    "matching_partner_ids": [public_partner_for_gap.id],
                }
            ],
            recommended_partners=[
                {
                    "partner_id": public_partner_for_gap.id,
                    "name": "Gap Analysis Partner",
                    "reason": "Capability match",
                }
            ],
            analysis_summary="One gap identified.",
        )

        with patch(
            "app.api.routes.teaming_board.gap_analysis.analyze_capability_gaps",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            resp = await client.get(f"{BASE}/gap-analysis/{rfp_for_gap.id}", headers=auth_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["rfp_id"] == rfp_for_gap.id
            assert len(data["gaps"]) == 1
            assert data["gaps"][0]["gap_type"] == "technical"
            assert len(data["recommended_partners"]) == 1
            assert data["analysis_summary"] == "One gap identified."

    @pytest.mark.asyncio
    async def test_gap_analysis_idor_other_user_rfp(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        rfp_for_gap: RFP,
    ) -> None:
        """A second user can still request gap analysis on any RFP (no ownership check)."""
        user2 = User(
            email="user2@example.com",
            hashed_password=hash_password("Password123!"),
            full_name="User Two",
            company_name="Other Co",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(user2)
        await db_session.commit()
        await db_session.refresh(user2)
        tokens = create_token_pair(user2.id, user2.email, user2.tier)
        headers2 = {"Authorization": f"Bearer {tokens.access_token}"}

        mock_result = CapabilityGapResult(
            rfp_id=rfp_for_gap.id,
            gaps=[],
            recommended_partners=[],
            analysis_summary="No gaps.",
        )
        with patch(
            "app.api.routes.teaming_board.gap_analysis.analyze_capability_gaps",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            resp = await client.get(f"{BASE}/gap-analysis/{rfp_for_gap.id}", headers=headers2)
            # The endpoint does not enforce RFP ownership
            assert resp.status_code == 200
