"""
Integration tests for inbox.py — /api/v1/collaboration/workspaces/{workspace_id}/inbox
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def _create_workspace_and_member(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict,
    test_user: User,
) -> int:
    """Helper to create a workspace so inbox tests have a valid workspace_id.

    The collaboration routes create workspaces, so we call them directly.
    """
    resp = await client.post(
        "/api/v1/collaboration/workspaces",
        headers=auth_headers,
        json={"name": "Test Workspace", "description": "For inbox tests"},
    )
    # If workspace creation works, return the id; if not, create directly in DB
    if resp.status_code in (200, 201):
        return resp.json()["id"]
    # Fallback: create workspace directly via model
    from app.models.collaboration import SharedWorkspace, WorkspaceMember, WorkspaceRole

    ws = SharedWorkspace(
        name="Test Workspace",
        owner_id=test_user.id,
    )
    db_session.add(ws)
    await db_session.flush()
    member = WorkspaceMember(
        workspace_id=ws.id,
        user_id=test_user.id,
        role=WorkspaceRole.ADMIN,
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(ws)
    return ws.id


class TestListInboxMessages:
    """Tests for GET /api/v1/collaboration/workspaces/{workspace_id}/inbox."""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/collaboration/workspaces/1/inbox")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_workspace_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(
            "/api/v1/collaboration/workspaces/99999/inbox", headers=auth_headers
        )
        # Either 404 or 403 depending on workspace membership check
        assert response.status_code in (403, 404)

    @pytest.mark.asyncio
    async def test_list_empty(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        ws_id = await _create_workspace_and_member(client, db_session, auth_headers, test_user)
        response = await client.get(
            f"/api/v1/collaboration/workspaces/{ws_id}/inbox",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0


class TestSendInboxMessage:
    """Tests for POST /api/v1/collaboration/workspaces/{workspace_id}/inbox."""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/collaboration/workspaces/1/inbox",
            json={"subject": "Hello", "body": "Test"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_send_message(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        ws_id = await _create_workspace_and_member(client, db_session, auth_headers, test_user)
        response = await client.post(
            f"/api/v1/collaboration/workspaces/{ws_id}/inbox",
            headers=auth_headers,
            json={"subject": "New Opportunity", "body": "Check this RFP"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["subject"] == "New Opportunity"
        assert data["sender_id"] == test_user.id

    @pytest.mark.asyncio
    async def test_invalid_message_type(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        ws_id = await _create_workspace_and_member(client, db_session, auth_headers, test_user)
        response = await client.post(
            f"/api/v1/collaboration/workspaces/{ws_id}/inbox",
            headers=auth_headers,
            json={
                "subject": "Bad Type",
                "body": "Content",
                "message_type": "nonexistent_type",
            },
        )
        assert response.status_code == 400


class TestMarkMessageRead:
    """Tests for PATCH /api/v1/collaboration/workspaces/{workspace_id}/inbox/{message_id}/read."""

    @pytest.mark.asyncio
    async def test_mark_read(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        ws_id = await _create_workspace_and_member(client, db_session, auth_headers, test_user)
        send_resp = await client.post(
            f"/api/v1/collaboration/workspaces/{ws_id}/inbox",
            headers=auth_headers,
            json={"subject": "Read Me", "body": "Content"},
        )
        msg_id = send_resp.json()["id"]

        response = await client.patch(
            f"/api/v1/collaboration/workspaces/{ws_id}/inbox/{msg_id}/read",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["is_read"] is True

    @pytest.mark.asyncio
    async def test_mark_read_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        ws_id = await _create_workspace_and_member(client, db_session, auth_headers, test_user)
        response = await client.patch(
            f"/api/v1/collaboration/workspaces/{ws_id}/inbox/99999/read",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestDeleteInboxMessage:
    """Tests for DELETE /api/v1/collaboration/workspaces/{workspace_id}/inbox/{message_id}."""

    @pytest.mark.asyncio
    async def test_delete_own_message(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        ws_id = await _create_workspace_and_member(client, db_session, auth_headers, test_user)
        send_resp = await client.post(
            f"/api/v1/collaboration/workspaces/{ws_id}/inbox",
            headers=auth_headers,
            json={"subject": "Delete Me", "body": "Content"},
        )
        msg_id = send_resp.json()["id"]

        response = await client.delete(
            f"/api/v1/collaboration/workspaces/{ws_id}/inbox/{msg_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        ws_id = await _create_workspace_and_member(client, db_session, auth_headers, test_user)
        response = await client.delete(
            f"/api/v1/collaboration/workspaces/{ws_id}/inbox/99999",
            headers=auth_headers,
        )
        assert response.status_code == 404
