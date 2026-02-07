"""
RFP Sniper - API Routes
========================
Route module exports.
"""

from app.api.routes.activity import router as activity_router
from app.api.routes.admin import router as admin_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.analytics_reporting import router as analytics_reporting_router
from app.api.routes.analyze import router as analyze_router
from app.api.routes.audit import router as audit_router
from app.api.routes.auth import router as auth_router
from app.api.routes.awards import router as awards_router
from app.api.routes.budget_intel import router as budget_intel_router
from app.api.routes.capture import router as capture_router
from app.api.routes.capture_timeline import router as capture_timeline_router
from app.api.routes.collaboration import router as collaboration_router
from app.api.routes.compliance_dashboard import router as compliance_router
from app.api.routes.contacts import router as contacts_router
from app.api.routes.contracts import router as contracts_router
from app.api.routes.dash import router as dash_router
from app.api.routes.data_sources import router as data_sources_router
from app.api.routes.documents import router as documents_router
from app.api.routes.draft import router as draft_router
from app.api.routes.email_ingest import router as email_ingest_router
from app.api.routes.events import router as events_router
from app.api.routes.export import router as export_router
from app.api.routes.forecasts import router as forecasts_router
from app.api.routes.graphics import router as graphics_router
from app.api.routes.health import router as health_router
from app.api.routes.ingest import router as ingest_router
from app.api.routes.integrations import router as integrations_router
from app.api.routes.intelligence import router as intelligence_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.reports import router as reports_router
from app.api.routes.revenue import router as revenue_router
from app.api.routes.reviews import router as reviews_router
from app.api.routes.rfps import router as rfps_router
from app.api.routes.salesforce import router as salesforce_router
from app.api.routes.saved_searches import router as saved_searches_router
from app.api.routes.scim import router as scim_router
from app.api.routes.search import router as search_router
from app.api.routes.secrets import router as secrets_router
from app.api.routes.sharepoint import router as sharepoint_router
from app.api.routes.sharepoint_sync import router as sharepoint_sync_router
from app.api.routes.signals import router as signals_router
from app.api.routes.subscription import router as subscription_router
from app.api.routes.teaming_board import router as teaming_board_router
from app.api.routes.teams import router as teams_router
from app.api.routes.templates import router as templates_router
from app.api.routes.templates_marketplace import router as templates_marketplace_router
from app.api.routes.unanet import router as unanet_router
from app.api.routes.versions import router as versions_router
from app.api.routes.webhooks import router as webhooks_router
from app.api.routes.websocket import router as websocket_router
from app.api.routes.word_addin import router as word_addin_router
from app.api.routes.workflows import router as workflows_router

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
    "templates_marketplace_router",
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
    "saved_searches_router",
    "awards_router",
    "contacts_router",
    "word_addin_router",
    "graphics_router",
    "scim_router",
    "secrets_router",
    "budget_intel_router",
    "revenue_router",
    "capture_timeline_router",
    "forecasts_router",
    "teaming_board_router",
    "collaboration_router",
    "sharepoint_router",
    "sharepoint_sync_router",
    "data_sources_router",
    "salesforce_router",
    "analytics_reporting_router",
    "reviews_router",
    "subscription_router",
    "search_router",
    "events_router",
    "signals_router",
    "email_ingest_router",
    "workflows_router",
    "compliance_router",
    "unanet_router",
    "reports_router",
    "activity_router",
    "intelligence_router",
    "admin_router",
]
