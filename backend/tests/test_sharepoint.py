"""
RFP Sniper - SharePoint Route Tests
===================================
Integration tests for SharePoint browse/download/export/status routes.
"""

import pytest
from httpx import AsyncClient

from app.models.proposal import Proposal, ProposalSection
from app.models.rfp import RFP
from app.models.user import User


class _FakeSharePointService:
    def __init__(self) -> None:
        self.uploads: list[tuple[str, str, bytes]] = []

    async def list_files(self, path: str):
        if path == "/":
            return [
                {
                    "id": "folder-1",
                    "name": "Proposals",
                    "is_folder": True,
                    "size": 0,
                    "last_modified": None,
                    "web_url": None,
                },
                {
                    "id": "file-1",
                    "name": "capture-plan.docx",
                    "is_folder": False,
                    "size": 2048,
                    "last_modified": "2026-02-10T12:00:00Z",
                    "web_url": "https://example.sharepoint.com/file-1",
                },
            ]
        return []

    async def download_file(self, file_id: str) -> bytes:
        return f"download-{file_id}".encode()

    async def upload_file(self, folder: str, name: str, content: bytes):
        self.uploads.append((folder, name, content))
        return {
            "id": "upload-1",
            "name": name,
            "web_url": f"https://example.sharepoint.com/{name}",
            "size": len(content),
        }


async def _create_sharepoint_integration(client: AsyncClient, auth_headers: dict) -> None:
    response = await client.post(
        "/api/v1/integrations",
        headers=auth_headers,
        json={
            "provider": "sharepoint",
            "name": "SharePoint",
            "is_enabled": True,
            "config": {
                "site_url": "https://example.sharepoint.com/sites/demo",
                "tenant_id": "tenant",
                "client_id": "client",
                "client_secret": "secret",
            },
        },
    )
    assert response.status_code == 200, response.text


class TestSharePointRoutes:
    @pytest.mark.asyncio
    async def test_browse_download_and_status(
        self,
        client: AsyncClient,
        auth_headers: dict,
        monkeypatch: pytest.MonkeyPatch,
    ):
        fake_sp = _FakeSharePointService()
        monkeypatch.setattr(
            "app.api.routes.sharepoint.create_sharepoint_service",
            lambda _config: fake_sp,
        )
        await _create_sharepoint_integration(client, auth_headers)

        status_response = await client.get("/api/v1/sharepoint/status", headers=auth_headers)
        assert status_response.status_code == 200
        assert status_response.json() == {
            "configured": True,
            "enabled": True,
            "connected": True,
        }

        browse_response = await client.get(
            "/api/v1/sharepoint/browse",
            headers=auth_headers,
            params={"path": "/"},
        )
        assert browse_response.status_code == 200
        files = browse_response.json()
        assert len(files) == 2
        assert files[1]["name"] == "capture-plan.docx"

        download_response = await client.get(
            "/api/v1/sharepoint/download/file-1",
            headers=auth_headers,
        )
        assert download_response.status_code == 200
        assert download_response.content == b"download-file-1"

    @pytest.mark.asyncio
    async def test_export_uploads_generated_docx(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        test_rfp: RFP,
        db_session,
        monkeypatch: pytest.MonkeyPatch,
    ):
        proposal = Proposal(
            user_id=test_user.id,
            rfp_id=test_rfp.id,
            title="SharePoint Export Proposal",
            status="draft",
            total_sections=1,
            completed_sections=0,
        )
        db_session.add(proposal)
        await db_session.commit()
        await db_session.refresh(proposal)

        section = ProposalSection(
            proposal_id=proposal.id,
            title="Executive Summary",
            section_number="1.0",
            requirement_text="Summarize key strengths.",
            final_content="Export body content.",
            display_order=1,
        )
        db_session.add(section)
        await db_session.commit()

        fake_sp = _FakeSharePointService()
        monkeypatch.setattr(
            "app.api.routes.sharepoint.create_sharepoint_service",
            lambda _config: fake_sp,
        )
        monkeypatch.setattr(
            "app.api.routes.export.create_docx_proposal",
            lambda _proposal, _sections, _rfp: b"docx-bytes",
        )

        await _create_sharepoint_integration(client, auth_headers)

        export_response = await client.post(
            "/api/v1/sharepoint/export",
            headers=auth_headers,
            params={
                "proposal_id": proposal.id,
                "folder": "/Proposals",
                "format": "docx",
            },
        )
        assert export_response.status_code == 200, export_response.text
        payload = export_response.json()
        assert payload["name"].endswith(".docx")
        assert payload["size"] == len(b"docx-bytes")

        assert len(fake_sp.uploads) == 1
        folder, filename, content = fake_sp.uploads[0]
        assert folder == "/Proposals"
        assert filename.endswith(".docx")
        assert content == b"docx-bytes"
