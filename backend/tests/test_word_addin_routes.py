"""
Integration tests for word_addin.py — /api/v1/word-addin/
"""

from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.proposal import Proposal, ProposalSection
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password


class TestListWordAddinSessions:
    """Tests for GET /api/v1/word-addin/sessions."""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/word-addin/sessions")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_empty(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/word-addin/sessions", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []


class TestCreateWordAddinSession:
    """Tests for POST /api/v1/word-addin/sessions."""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/word-addin/sessions",
            json={"proposal_id": 1, "document_name": "test.docx"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_session(
        self, client: AsyncClient, auth_headers: dict, test_proposal: Proposal
    ):
        response = await client.post(
            "/api/v1/word-addin/sessions",
            headers=auth_headers,
            json={
                "proposal_id": test_proposal.id,
                "document_name": "proposal_v1.docx",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["proposal_id"] == test_proposal.id
        assert data["document_name"] == "proposal_v1.docx"
        assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_create_proposal_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/word-addin/sessions",
            headers=auth_headers,
            json={"proposal_id": 99999, "document_name": "ghost.docx"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_proposal: Proposal,
    ):
        """User B cannot create session for User A's proposal."""
        user_b = User(
            email="other@example.com",
            hashed_password=hash_password("Pwd123!"),
            full_name="Other",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(user_b)
        await db_session.commit()
        await db_session.refresh(user_b)
        tokens = create_token_pair(user_b.id, user_b.email, user_b.tier)
        headers_b = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.post(
            "/api/v1/word-addin/sessions",
            headers=headers_b,
            json={"proposal_id": test_proposal.id, "document_name": "hack.docx"},
        )
        assert response.status_code == 404


class TestUpdateWordAddinSession:
    """Tests for PATCH /api/v1/word-addin/sessions/{session_id}."""

    @pytest.mark.asyncio
    async def test_update_session(
        self, client: AsyncClient, auth_headers: dict, test_proposal: Proposal
    ):
        create_resp = await client.post(
            "/api/v1/word-addin/sessions",
            headers=auth_headers,
            json={"proposal_id": test_proposal.id, "document_name": "v1.docx"},
        )
        sid = create_resp.json()["id"]

        response = await client.patch(
            f"/api/v1/word-addin/sessions/{sid}",
            headers=auth_headers,
            json={"document_name": "v2.docx", "status": "paused"},
        )
        assert response.status_code == 200
        assert response.json()["document_name"] == "v2.docx"
        assert response.json()["status"] == "paused"

    @pytest.mark.asyncio
    async def test_update_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.patch(
            "/api/v1/word-addin/sessions/99999",
            headers=auth_headers,
            json={"document_name": "ghost.docx"},
        )
        assert response.status_code == 404


class TestWordAddinEvents:
    """Tests for POST/GET /api/v1/word-addin/sessions/{session_id}/events."""

    @pytest.mark.asyncio
    async def test_create_event(
        self, client: AsyncClient, auth_headers: dict, test_proposal: Proposal
    ):
        create_resp = await client.post(
            "/api/v1/word-addin/sessions",
            headers=auth_headers,
            json={"proposal_id": test_proposal.id, "document_name": "ev.docx"},
        )
        sid = create_resp.json()["id"]

        response = await client.post(
            f"/api/v1/word-addin/sessions/{sid}/events",
            headers=auth_headers,
            json={"event_type": "content_sync", "payload": {"section_id": 1}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["event_type"] == "content_sync"
        assert data["session_id"] == sid

    @pytest.mark.asyncio
    async def test_list_events(
        self, client: AsyncClient, auth_headers: dict, test_proposal: Proposal
    ):
        create_resp = await client.post(
            "/api/v1/word-addin/sessions",
            headers=auth_headers,
            json={"proposal_id": test_proposal.id, "document_name": "list_ev.docx"},
        )
        sid = create_resp.json()["id"]

        # Create an event
        await client.post(
            f"/api/v1/word-addin/sessions/{sid}/events",
            headers=auth_headers,
            json={"event_type": "open"},
        )

        response = await client.get(
            f"/api/v1/word-addin/sessions/{sid}/events", headers=auth_headers
        )
        assert response.status_code == 200
        assert len(response.json()) == 1

    @pytest.mark.asyncio
    async def test_events_session_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(
            "/api/v1/word-addin/sessions/99999/events", headers=auth_headers
        )
        assert response.status_code == 404


class TestSectionPull:
    """Tests for POST /api/v1/word-addin/sections/{section_id}/pull."""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/word-addin/sections/1/pull")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_pull_section(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_proposal: Proposal,
    ):
        section = ProposalSection(
            proposal_id=test_proposal.id,
            title="Executive Summary",
            section_number="1",
            display_order=1,
            final_content="Our approach to cybersecurity...",
        )
        db_session.add(section)
        await db_session.commit()
        await db_session.refresh(section)

        response = await client.post(
            f"/api/v1/word-addin/sections/{section.id}/pull",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Executive Summary"
        assert "cybersecurity" in data["content"]

    @pytest.mark.asyncio
    async def test_pull_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.post("/api/v1/word-addin/sections/99999/pull", headers=auth_headers)
        assert response.status_code == 404


class TestSectionPush:
    """Tests for POST /api/v1/word-addin/sections/{section_id}/push."""

    @pytest.mark.asyncio
    async def test_push_section(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_proposal: Proposal,
    ):
        section = ProposalSection(
            proposal_id=test_proposal.id,
            title="Technical Approach",
            section_number="2",
            display_order=2,
        )
        db_session.add(section)
        await db_session.commit()
        await db_session.refresh(section)

        response = await client.post(
            f"/api/v1/word-addin/sections/{section.id}/push",
            headers=auth_headers,
            json={"content": "Updated from Word add-in"},
        )
        assert response.status_code == 200
        assert response.json()["section_id"] == section.id


class TestComplianceCheck:
    """Tests for POST /api/v1/word-addin/sections/{section_id}/compliance-check."""

    @pytest.mark.asyncio
    async def test_compliance_check(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_proposal: Proposal,
    ):
        section = ProposalSection(
            proposal_id=test_proposal.id,
            title="Management",
            section_number="3",
            display_order=3,
            final_content="We will provide comprehensive program management with experienced staff.",
        )
        db_session.add(section)
        await db_session.commit()
        await db_session.refresh(section)

        response = await client.post(
            f"/api/v1/word-addin/sections/{section.id}/compliance-check",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "compliant" in data
        assert "score" in data
        assert "issues" in data

    @pytest.mark.asyncio
    async def test_compliance_empty_content(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_proposal: Proposal,
    ):
        """Empty section content should flag critical issue."""
        section = ProposalSection(
            proposal_id=test_proposal.id,
            title="Empty",
            section_number="4",
            display_order=4,
            final_content="",
        )
        db_session.add(section)
        await db_session.commit()
        await db_session.refresh(section)

        response = await client.post(
            f"/api/v1/word-addin/sections/{section.id}/compliance-check",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["compliant"] is False
        assert any(i["severity"] == "critical" for i in data["issues"])


class TestAIRewrite:
    """Tests for POST /api/v1/word-addin/ai/rewrite."""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/word-addin/ai/rewrite",
            json={"content": "Test", "mode": "improve"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_mode(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/word-addin/ai/rewrite",
            headers=auth_headers,
            json={"content": "Test content", "mode": "invalid_mode"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    @patch("app.api.routes.word_addin.settings")
    async def test_rewrite_mock_mode(self, mock_settings, client: AsyncClient, auth_headers: dict):
        """When mock_ai=True, returns deterministic rewrite."""
        mock_settings.mock_ai = True
        response = await client.post(
            "/api/v1/word-addin/ai/rewrite",
            headers=auth_headers,
            json={"content": "Our approach is comprehensive.", "mode": "shorten"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "shorten"
        assert data["original_length"] > 0
        assert data["rewritten_length"] > 0
