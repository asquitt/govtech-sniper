"""
Admin route helpers.
"""

import socket
from urllib.parse import urlparse

import structlog
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import UserAuth
from app.config import settings
from app.models.organization import (
    Organization,
    OrganizationMember,
    OrgRole,
)
from app.models.user import User

logger = structlog.get_logger(__name__)


async def _require_org_admin(
    user: UserAuth,
    session: AsyncSession,
) -> tuple[Organization, OrganizationMember]:
    """Verify user is an admin or owner of their organization."""
    db_user = (await session.execute(select(User).where(User.id == user.id))).scalar_one_or_none()
    if not db_user or not db_user.organization_id:
        raise HTTPException(status_code=403, detail="No organization membership")

    org = (
        await session.execute(
            select(Organization).where(Organization.id == db_user.organization_id)
        )
    ).scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    member = (
        await session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org.id,
                OrganizationMember.user_id == user.id,
                OrganizationMember.is_active == True,  # noqa: E712
            )
        )
    ).scalar_one_or_none()
    if not member or member.role not in (OrgRole.OWNER, OrgRole.ADMIN):
        raise HTTPException(status_code=403, detail="Admin access required")

    return org, member


def _celery_broker_available() -> bool:
    """
    Best-effort broker probe for capability diagnostics.
    """
    broker_url = settings.celery_broker_url
    parsed = urlparse(broker_url)
    if parsed.scheme not in {"redis", "rediss"}:
        return True

    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    try:
        with socket.create_connection((host, port), timeout=0.2):
            return True
    except OSError:
        return False


def _celery_worker_available() -> bool:
    """
    Best-effort worker availability probe for local/dev diagnostics.
    """
    try:
        from app.tasks.celery_app import celery_app

        replies = celery_app.control.inspect(timeout=0.5).ping() or {}
        return len(replies) > 0
    except Exception:
        return False


def _database_engine_name(database_url: str) -> str:
    normalized = database_url.lower()
    if "sqlite" in normalized:
        return "sqlite"
    if "postgres" in normalized:
        return "postgresql"
    if "mysql" in normalized:
        return "mysql"
    return "unknown"


def _websocket_runtime_snapshot() -> dict[str, int]:
    """
    Best-effort snapshot of websocket runtime state for diagnostics.
    """
    try:
        from app.api.routes.websocket import manager

        active_connections = sum(
            len(connections) for connections in manager.active_connections.values()
        )
        watched_tasks = len(manager.task_watchers)
        active_documents = len(manager.document_presence)
        presence_users = sum(len(users) for users in manager.document_presence.values())
        active_section_locks = len(manager.section_locks)
        active_cursors = sum(len(cursors) for cursors in manager.document_cursors.values())
        return {
            "active_connections": active_connections,
            "watched_tasks": watched_tasks,
            "active_documents": active_documents,
            "presence_users": presence_users,
            "active_section_locks": active_section_locks,
            "active_cursors": active_cursors,
        }
    except Exception:
        return {
            "active_connections": 0,
            "watched_tasks": 0,
            "active_documents": 0,
            "presence_users": 0,
            "active_section_locks": 0,
            "active_cursors": 0,
        }
