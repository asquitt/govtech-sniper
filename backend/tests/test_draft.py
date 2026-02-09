"""
RFP Sniper - Draft Tests
========================
Tests for proposal listing endpoints.
"""

import pytest
from httpx import AsyncClient

from app.models.rfp import RFP, ComplianceMatrix
from app.models.user import User


class TestDraftProposals:
    @pytest.mark.asyncio
    async def test_list_proposals(self, client: AsyncClient, test_user: User, test_rfp: RFP):
        # Create proposal
        response = await client.post(
            "/api/v1/draft/proposals",
            params={"user_id": test_user.id},
            json={"rfp_id": test_rfp.id, "title": "Test Proposal"},
        )
        assert response.status_code == 200

        # List proposals
        response = await client.get(
            "/api/v1/draft/proposals",
            params={"user_id": test_user.id},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Test Proposal"

    @pytest.mark.asyncio
    async def test_section_evidence_and_submission_packages(
        self,
        client: AsyncClient,
        test_user: User,
        test_rfp: RFP,
        test_document,
    ):
        # Create proposal
        response = await client.post(
            "/api/v1/draft/proposals",
            params={"user_id": test_user.id},
            json={"rfp_id": test_rfp.id, "title": "Evidence Proposal"},
        )
        assert response.status_code == 200
        proposal_id = response.json()["id"]

        # Create section
        response = await client.post(
            f"/api/v1/draft/proposals/{proposal_id}/sections",
            json={
                "title": "Technical Approach",
                "section_number": "1.1",
                "requirement_text": "Provide an approach to meet requirements.",
                "display_order": 0,
            },
        )
        assert response.status_code == 200
        section_id = response.json()["id"]

        # Update section
        response = await client.patch(
            f"/api/v1/draft/sections/{section_id}",
            params={"user_id": test_user.id},
            json={"final_content": "We propose an agile delivery model."},
        )
        assert response.status_code == 200
        assert response.json()["final_content"] == "We propose an agile delivery model."

        # Add evidence
        response = await client.post(
            f"/api/v1/draft/sections/{section_id}/evidence",
            params={"user_id": test_user.id},
            json={
                "document_id": test_document.id,
                "citation": "Capability Statement, page 2",
            },
        )
        assert response.status_code == 200
        evidence_id = response.json()["id"]

        # List evidence
        response = await client.get(
            f"/api/v1/draft/sections/{section_id}/evidence",
            params={"user_id": test_user.id},
        )
        assert response.status_code == 200
        evidence = response.json()
        assert len(evidence) == 1
        assert evidence[0]["id"] == evidence_id

        # Create submission package
        response = await client.post(
            f"/api/v1/draft/proposals/{proposal_id}/submission-packages",
            params={"user_id": test_user.id},
            json={"title": "Final Package"},
        )
        assert response.status_code == 200
        package_id = response.json()["id"]

        # Update submission package
        response = await client.patch(
            f"/api/v1/draft/submission-packages/{package_id}",
            params={"user_id": test_user.id},
            json={"notes": "Ready for export"},
        )
        assert response.status_code == 200
        assert response.json()["notes"] == "Ready for export"

        # Submit package
        response = await client.post(
            f"/api/v1/draft/submission-packages/{package_id}/submit",
            params={"user_id": test_user.id},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "submitted"

    @pytest.mark.asyncio
    async def test_generate_from_matrix_skips_existing_sections(
        self,
        client: AsyncClient,
        db_session,
        test_user: User,
        test_rfp: RFP,
    ):
        matrix = ComplianceMatrix(
            rfp_id=test_rfp.id,
            requirements=[
                {
                    "id": "REQ-001",
                    "section": "L.1",
                    "requirement_text": "Provide implementation plan",
                    "importance": "mandatory",
                },
                {
                    "id": "REQ-002",
                    "section": "M.1",
                    "requirement_text": "Provide staffing approach",
                    "importance": "evaluated",
                },
            ],
            total_requirements=2,
            mandatory_count=1,
            addressed_count=0,
        )
        db_session.add(matrix)
        await db_session.commit()

        create_proposal = await client.post(
            "/api/v1/draft/proposals",
            params={"user_id": test_user.id},
            json={"rfp_id": test_rfp.id, "title": "Matrix Proposal"},
        )
        assert create_proposal.status_code == 200
        proposal_id = create_proposal.json()["id"]

        first_run = await client.post(f"/api/v1/draft/proposals/{proposal_id}/generate-from-matrix")
        assert first_run.status_code == 200
        assert first_run.json()["sections_created"] == 2

        second_run = await client.post(
            f"/api/v1/draft/proposals/{proposal_id}/generate-from-matrix"
        )
        assert second_run.status_code == 200
        assert second_run.json()["sections_created"] == 0

        sections = await client.get(
            f"/api/v1/draft/proposals/{proposal_id}/sections",
            params={"user_id": test_user.id},
        )
        assert sections.status_code == 200
        assert len(sections.json()) == 2

    @pytest.mark.asyncio
    async def test_generate_section_sync_fallback_and_status(
        self,
        client: AsyncClient,
        test_user: User,
        test_rfp: RFP,
        monkeypatch,
    ):
        from app.api.routes.draft import generation

        monkeypatch.setattr(generation, "_celery_broker_available", lambda: False)
        monkeypatch.setattr(generation.settings, "mock_ai", True)
        monkeypatch.setattr(generation.settings, "gemini_api_key", None)

        create_proposal = await client.post(
            "/api/v1/draft/proposals",
            params={"user_id": test_user.id},
            json={"rfp_id": test_rfp.id, "title": "Sync Draft Proposal"},
        )
        assert create_proposal.status_code == 200
        proposal_id = create_proposal.json()["id"]

        create_section = await client.post(
            f"/api/v1/draft/proposals/{proposal_id}/sections",
            json={
                "title": "Technical Approach",
                "section_number": "1.1",
                "requirement_id": "REQ-001",
                "requirement_text": "Describe technical approach.",
                "display_order": 0,
            },
        )
        assert create_section.status_code == 200
        section_id = create_section.json()["id"]

        generate = await client.post(
            "/api/v1/draft/REQ-001",
            params={"user_id": test_user.id},
            json={"requirement_id": "REQ-001", "rfp_id": test_rfp.id},
        )
        assert generate.status_code == 200
        generate_data = generate.json()
        assert generate_data["status"] == "completed"
        assert generate_data["section_id"] == section_id
        assert generate_data["task_id"].startswith("sync-")

        status = await client.get(f"/api/v1/draft/{generate_data['task_id']}/status")
        assert status.status_code == 200
        status_data = status.json()
        assert status_data["status"] == "completed"
        assert status_data["result"]["section_id"] == section_id

        section = await client.get(
            f"/api/v1/draft/sections/{section_id}",
            params={"user_id": test_user.id},
        )
        assert section.status_code == 200
        section_data = section.json()
        assert section_data["status"] == "generated"
        assert section_data["generated_content"]["model_used"] == "mock"

    @pytest.mark.asyncio
    async def test_generate_section_sync_fallback_when_worker_unavailable(
        self,
        client: AsyncClient,
        test_user: User,
        test_rfp: RFP,
        monkeypatch,
    ):
        from app.api.routes.draft import generation

        monkeypatch.setattr(generation, "_celery_broker_available", lambda: True)
        monkeypatch.setattr(generation, "_celery_worker_available", lambda: False)
        monkeypatch.setattr(generation.settings, "mock_ai", True)
        monkeypatch.setattr(generation.settings, "gemini_api_key", None)

        create_proposal = await client.post(
            "/api/v1/draft/proposals",
            params={"user_id": test_user.id},
            json={"rfp_id": test_rfp.id, "title": "Workerless Sync Draft Proposal"},
        )
        assert create_proposal.status_code == 200
        proposal_id = create_proposal.json()["id"]

        create_section = await client.post(
            f"/api/v1/draft/proposals/{proposal_id}/sections",
            json={
                "title": "Technical Approach",
                "section_number": "1.1",
                "requirement_id": "REQ-001",
                "requirement_text": "Describe technical approach.",
                "display_order": 0,
            },
        )
        assert create_section.status_code == 200

        generate = await client.post(
            "/api/v1/draft/REQ-001",
            params={"user_id": test_user.id},
            json={"requirement_id": "REQ-001", "rfp_id": test_rfp.id},
        )
        assert generate.status_code == 200
        generate_data = generate.json()
        assert generate_data["status"] == "completed"
        assert generate_data["task_id"].startswith("sync-")
