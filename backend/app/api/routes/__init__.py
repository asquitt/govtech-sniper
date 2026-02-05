"""
RFP Sniper - API Routes
========================
Route module exports.
"""

from app.api.routes.ingest import router as ingest_router
from app.api.routes.analyze import router as analyze_router
from app.api.routes.draft import router as draft_router
from app.api.routes.rfps import router as rfps_router
from app.api.routes.documents import router as documents_router
from app.api.routes.health import router as health_router
from app.api.routes.auth import router as auth_router
from app.api.routes.websocket import router as websocket_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.templates import router as templates_router
from app.api.routes.export import router as export_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.teams import router as teams_router
from app.api.routes.versions import router as versions_router
from app.api.routes.integrations import router as integrations_router
from app.api.routes.webhooks import router as webhooks_router
from app.api.routes.dash import router as dash_router
from app.api.routes.capture import router as capture_router
from app.api.routes.contracts import router as contracts_router
from app.api.routes.audit import router as audit_router

__all__ = [
    "ingest_router",
    "analyze_router",
    "draft_router",
    "rfps_router",
    "documents_router",
    "health_router",
    "auth_router",
    "websocket_router",
    "analytics_router",
    "templates_router",
    "export_router",
    "notifications_router",
    "teams_router",
    "versions_router",
    "integrations_router",
    "webhooks_router",
    "dash_router",
    "capture_router",
    "contracts_router",
    "audit_router",
]
