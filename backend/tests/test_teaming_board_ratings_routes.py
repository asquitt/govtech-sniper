"""
Tests for teaming_board/ratings routes - Partner performance ratings.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capture import TeamingPartner, TeamingPerformanceRating
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password

BASE = "/api/v1/teaming"


@pytest_asyncio.fixture
async def partner(db_session: AsyncSession, test_user: User) -> TeamingPartner:
    p = TeamingPartner(
        user_id=test_user.id,
        name="Rating Target Partner",
        is_public=True,
    )
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


@pytest_asyncio.fixture
async def existing_rating(
    db_session: AsyncSession, test_user: User, partner: TeamingPartner
) -> TeamingPerformanceRating:
    rating = TeamingPerformanceRating(
        user_id=test_user.id,
        partner_id=partner.id,
        rating=4,
        responsiveness=5,
        quality=4,
        timeliness=3,
        comment="Solid partner for cloud work.",
    )
    db_session.add(rating)
    await db_session.commit()
    await db_session.refresh(rating)
    return rating


class TestCreateRatingAuth:
    @pytest.mark.asyncio
    async def test_create_rating_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.post(f"{BASE}/ratings", json={"partner_id": 1, "rating": 5})
        assert resp.status_code == 401


class TestCreateRating:
    @pytest.mark.asyncio
    async def test_create_rating_minimal(
        self,
        client: AsyncClient,
        auth_headers: dict,
        partner: TeamingPartner,
    ) -> None:
        resp = await client.post(
            f"{BASE}/ratings",
            headers=auth_headers,
            json={"partner_id": partner.id, "rating": 5},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["partner_id"] == partner.id
        assert data["rating"] == 5
        assert data["responsiveness"] is None

    @pytest.mark.asyncio
    async def test_create_rating_full(
        self,
        client: AsyncClient,
        auth_headers: dict,
        partner: TeamingPartner,
    ) -> None:
        resp = await client.post(
            f"{BASE}/ratings",
            headers=auth_headers,
            json={
                "partner_id": partner.id,
                "rfp_id": None,
                "rating": 3,
                "responsiveness": 4,
                "quality": 2,
                "timeliness": 5,
                "comment": "Mixed results on this contract.",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["rating"] == 3
        assert data["responsiveness"] == 4
        assert data["quality"] == 2
        assert data["timeliness"] == 5
        assert data["comment"] == "Mixed results on this contract."

    @pytest.mark.asyncio
    async def test_create_rating_response_has_user_id(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        partner: TeamingPartner,
    ) -> None:
        resp = await client.post(
            f"{BASE}/ratings",
            headers=auth_headers,
            json={"partner_id": partner.id, "rating": 4},
        )
        assert resp.status_code == 201
        assert resp.json()["user_id"] == test_user.id


class TestListPartnerRatings:
    @pytest.mark.asyncio
    async def test_list_ratings_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get(f"{BASE}/partners/1/ratings")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_list_ratings_returns_existing(
        self,
        client: AsyncClient,
        auth_headers: dict,
        partner: TeamingPartner,
        existing_rating: TeamingPerformanceRating,
    ) -> None:
        resp = await client.get(f"{BASE}/partners/{partner.id}/ratings", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == existing_rating.id
        assert data[0]["rating"] == 4

    @pytest.mark.asyncio
    async def test_list_ratings_empty_for_unknown_partner(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.get(f"{BASE}/partners/99999/ratings", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_ratings_multiple(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
        partner: TeamingPartner,
        existing_rating: TeamingPerformanceRating,
    ) -> None:
        """Multiple ratings for the same partner should all be returned."""
        rating2 = TeamingPerformanceRating(
            user_id=test_user.id,
            partner_id=partner.id,
            rating=2,
            comment="Second engagement was disappointing.",
        )
        db_session.add(rating2)
        await db_session.commit()

        resp = await client.get(f"{BASE}/partners/{partner.id}/ratings", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    @pytest.mark.asyncio
    async def test_list_ratings_other_user_can_see(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        partner: TeamingPartner,
        existing_rating: TeamingPerformanceRating,
    ) -> None:
        """Ratings are visible to any authenticated user."""
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

        resp = await client.get(f"{BASE}/partners/{partner.id}/ratings", headers=headers2)
        assert resp.status_code == 200
        assert len(resp.json()) == 1
