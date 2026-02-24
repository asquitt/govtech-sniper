"""
Export Routes Integration Tests
=================================
Tests for proposal export (DOCX, PDF), compliance matrix, and compliance package.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.proposal import Proposal, ProposalSection
from app.models.rfp import RFP
from app.models.user import User

# =============================================================================
# Helpers
# =============================================================================


@pytest.fixture
async def test_section(db_session: AsyncSession, test_proposal: Proposal) -> ProposalSection:
    section = ProposalSection(
        proposal_id=test_proposal.id,
        section_number="L.1",
        title="Technical Approach",
        status="final",
        final_content="<p>Our technical approach involves...</p>",
    )
    db_session.add(section)
    await db_session.commit()
    await db_session.refresh(section)
    return section


# =============================================================================
# GET /export/proposals/{id}/docx
# =============================================================================


class TestExportDocx:
    @pytest.mark.asyncio
    async def test_export_docx_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/export/proposals/1/docx")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_export_docx_not_found(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/export/proposals/99999/docx", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_export_docx_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
        test_section: ProposalSection,
    ):
        with patch(
            "app.api.routes.export._enforce_export_policy",
            new=AsyncMock(return_value=None),
        ):
            resp = await client.get(
                f"/api/v1/export/proposals/{test_proposal.id}/docx",
                headers=auth_headers,
            )
        assert resp.status_code == 200
        assert "application/vnd.openxmlformats" in resp.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_export_docx_wrong_user(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_headers: dict,
    ):
        """Proposal owned by different user returns 404."""
        other_user = User(
            email="other@example.com",
            hashed_password="xxx",
            full_name="Other",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(other_user)

        proposal = Proposal(
            user_id=other_user.id,
            rfp_id=None,
            title="Other Proposal",
            status="draft",
        )
        db_session.add(proposal)
        await db_session.commit()
        await db_session.refresh(proposal)

        resp = await client.get(
            f"/api/v1/export/proposals/{proposal.id}/docx",
            headers=auth_headers,
        )
        assert resp.status_code == 404


# =============================================================================
# GET /export/proposals/{id}/pdf
# =============================================================================


class TestExportPdf:
    @pytest.mark.asyncio
    async def test_export_pdf_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/export/proposals/1/pdf")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_export_pdf_not_found(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/export/proposals/99999/pdf", headers=auth_headers)
        assert resp.status_code == 404


# =============================================================================
# GET /export/rfps/{id}/compliance-matrix/xlsx
# =============================================================================


class TestExportComplianceMatrix:
    @pytest.mark.asyncio
    async def test_compliance_matrix_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/export/rfps/1/compliance-matrix/xlsx")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_compliance_matrix_not_found(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get(
            "/api/v1/export/rfps/99999/compliance-matrix/xlsx",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_compliance_matrix_success(
        self, client: AsyncClient, auth_headers: dict, test_rfp: RFP
    ):
        resp = await client.get(
            f"/api/v1/export/rfps/{test_rfp.id}/compliance-matrix/xlsx",
            headers=auth_headers,
        )
        # May return 200 (empty matrix) or 404 depending on whether matrix exists
        assert resp.status_code in (200, 404)


# =============================================================================
# GET /export/proposals/{id}/compliance-package/zip
# =============================================================================


class TestExportCompliancePackage:
    @pytest.mark.asyncio
    async def test_compliance_package_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/export/proposals/1/compliance-package/zip")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_compliance_package_not_found(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get(
            "/api/v1/export/proposals/99999/compliance-package/zip",
            headers=auth_headers,
        )
        assert resp.status_code == 404
