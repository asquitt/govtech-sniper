"""
RFP Sniper - FastAPI Application Entry Point
=============================================
The main application that ties everything together.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.api.routes import (
    activity_router,
    admin_router,
    agents_router,
    analytics_reporting_router,
    analytics_router,
    analyze_router,
    audit_router,
    auth_router,
    awards_router,
    benchmark_router,
    budget_intel_router,
    capture_router,
    capture_timeline_router,
    collaboration_router,
    compliance_registry_router,
    compliance_router,
    contacts_router,
    contracts_router,
    dash_router,
    data_sources_router,
    documents_router,
    draft_router,
    email_ingest_router,
    events_router,
    export_router,
    forecasts_router,
    graphics_router,
    health_router,
    inbox_router,
    ingest_router,
    integrations_router,
    intelligence_router,
    kb_intelligence_router,
    notifications_router,
    onboarding_router,
    reports_router,
    revenue_router,
    reviews_router,
    rfps_router,
    salesforce_router,
    saved_searches_router,
    scim_router,
    search_router,
    secrets_router,
    sharepoint_router,
    sharepoint_sync_router,
    signals_router,
    subscription_router,
    support_router,
    teaming_board_router,
    teams_router,
    templates_marketplace_router,
    templates_router,
    unanet_router,
    versions_router,
    webhooks_router,
    websocket_router,
    word_addin_router,
    workflows_router,
)
from app.config import settings
from app.database import close_db, init_db
from app.observability import (
    MetricsMiddleware,
    get_logger,
    init_sentry,
    setup_logging,
)
from app.observability.logging import CorrelationIDMiddleware, RequestLoggingMiddleware
from app.observability.metrics import get_metrics
from app.observability.sentry import capture_exception

# Configure structured logging
setup_logging(
    log_level=settings.log_level,
    json_format=not settings.debug,
    include_timestamps=True,
)

# Initialize Sentry for error tracking
init_sentry(
    dsn=settings.sentry_dsn,
    environment=settings.sentry_environment,
    traces_sample_rate=settings.sentry_traces_sample_rate,
    release=f"{settings.app_name}@{settings.app_version}",
)

logger = get_logger(__name__)


# =============================================================================
# Application Lifecycle
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan manager.

    Handles startup and shutdown events:
    - Initialize database connection pool
    - Create tables (dev only)
    - Clean up on shutdown
    """
    logger.info(
        "Starting RFP Sniper API",
        version=settings.app_version,
        debug=settings.debug,
    )

    # Security: reject default secret keys in production
    _defaults = {"CHANGE_ME_IN_PRODUCTION", "CHANGE_ME_AUDIT_SIGNING"}
    if not settings.debug:
        if settings.secret_key in _defaults:
            raise RuntimeError(
                "SECRET_KEY is still the default value. "
                "Set a strong SECRET_KEY env var before running in production."
            )
        if settings.audit_export_signing_key in _defaults:
            raise RuntimeError(
                "AUDIT_EXPORT_SIGNING_KEY is still the default value. "
                "Set a strong AUDIT_EXPORT_SIGNING_KEY env var before running in production."
            )
    elif settings.secret_key in _defaults:
        logger.warning("Running with default SECRET_KEY — acceptable in debug mode only")

    # Startup
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down RFP Sniper API")
    await close_db()
    logger.info("Database connections closed")


# =============================================================================
# Create FastAPI Application
# =============================================================================

app = FastAPI(
    title=settings.app_name,
    description="""
## The RFP Sniper API

Automate the process of finding, analyzing, and writing proposals for US Government contracts.

### Key Features

- **SAM.gov Integration**: Automatically ingest opportunities from SAM.gov
- **Killer Filter**: AI-powered qualification screening using Gemini 1.5 Flash
- **Deep Read Analysis**: Extract compliance requirements from RFP documents
- **RAG-Powered Drafting**: Generate proposal sections with source citations
- **Citation Engine**: Track sources with [[Source: file.pdf, Page XX]] format

### Authentication

API authentication is handled via JWT tokens. All endpoints (except /health and /auth) require authentication.

### New Features (v2.0)

- **JWT Authentication**: Secure token-based authentication
- **Real-time Updates**: WebSocket support for task progress
- **Export**: Export proposals to DOCX/PDF
- **Templates**: Pre-built proposal response templates
- **Analytics**: Dashboard with usage metrics
- **Teams**: Collaboration and commenting
- **Notifications**: Email and Slack alerts for deadlines
    """,
    version=settings.app_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)


# =============================================================================
# Middleware
# =============================================================================


class MaxUploadSizeMiddleware:
    """Reject requests whose Content-Length exceeds the configured limit."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            content_length = headers.get(b"content-length")
            if content_length and int(content_length) > self.max_bytes:
                response = JSONResponse(
                    status_code=413,
                    content={
                        "detail": f"Request body too large. Max {self.max_bytes // (1024 * 1024)}MB."
                    },
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


# Upload size limit
app.add_middleware(
    MaxUploadSizeMiddleware,
    max_bytes=settings.max_upload_size_mb * 1024 * 1024,
)

# CORS middleware for frontend access
_cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Observability middleware stack (order matters - applied in reverse)
# 1. Metrics collection (innermost)
if settings.enable_metrics:
    app.add_middleware(MetricsMiddleware)

# 2. Request logging
app.add_middleware(RequestLoggingMiddleware, logger=logger)

# 3. Correlation ID (outermost)
app.add_middleware(CorrelationIDMiddleware)


# =============================================================================
# Exception Handlers
# =============================================================================


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled errors.
    Captures exceptions to Sentry and returns a safe error response.
    """
    # Capture to Sentry
    error_id = capture_exception(
        exc,
        context={
            "path": request.url.path,
            "method": request.method,
            "query_params": str(request.query_params),
        },
    )

    logger.error(
        "Unhandled exception",
        path=request.url.path,
        error=str(exc),
        error_id=error_id,
        exc_info=True,
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal error occurred. Please try again later.",
            "error_id": error_id or str(id(exc)),  # For support reference
        },
    )


# =============================================================================
# Register Routes
# =============================================================================

# Health checks (no auth required)
app.include_router(health_router)

# WebSocket (handles its own auth)
app.include_router(websocket_router)

# Core API routes
api_prefix = "/api/v1"

# Health checks under API prefix for clients/tests
app.include_router(health_router, prefix=api_prefix)

# Authentication (no auth required for login/register)
app.include_router(auth_router, prefix=api_prefix)

# WebSocket HTTP helpers under API prefix for frontend proxy consistency
app.include_router(websocket_router, prefix=api_prefix)

# Protected routes
app.include_router(ingest_router, prefix=api_prefix)
app.include_router(analyze_router, prefix=api_prefix)
app.include_router(draft_router, prefix=api_prefix)
app.include_router(rfps_router, prefix=api_prefix)
app.include_router(documents_router, prefix=api_prefix)
app.include_router(export_router, prefix=api_prefix)
app.include_router(templates_marketplace_router, prefix=api_prefix)
app.include_router(templates_router, prefix=api_prefix)
app.include_router(analytics_router, prefix=api_prefix)
app.include_router(notifications_router, prefix=api_prefix)
app.include_router(teams_router, prefix=api_prefix)
app.include_router(versions_router, prefix=api_prefix)
app.include_router(integrations_router, prefix=api_prefix)
app.include_router(webhooks_router, prefix=api_prefix)
app.include_router(dash_router, prefix=api_prefix)
app.include_router(capture_router, prefix=api_prefix)
app.include_router(contracts_router, prefix=api_prefix)
app.include_router(audit_router, prefix=api_prefix)
app.include_router(saved_searches_router, prefix=api_prefix)
app.include_router(awards_router, prefix=api_prefix)
app.include_router(contacts_router, prefix=api_prefix)
app.include_router(word_addin_router, prefix=api_prefix)
app.include_router(graphics_router, prefix=api_prefix)
app.include_router(scim_router, prefix=api_prefix)
app.include_router(secrets_router, prefix=api_prefix)
app.include_router(budget_intel_router, prefix=api_prefix)
app.include_router(revenue_router, prefix=api_prefix)
app.include_router(capture_timeline_router, prefix=api_prefix)
app.include_router(forecasts_router, prefix=api_prefix)
app.include_router(teaming_board_router, prefix=api_prefix)
app.include_router(collaboration_router, prefix=api_prefix)
app.include_router(sharepoint_router, prefix=api_prefix)
app.include_router(sharepoint_sync_router, prefix=api_prefix)
app.include_router(salesforce_router, prefix=api_prefix)
app.include_router(data_sources_router, prefix=api_prefix)
app.include_router(analytics_reporting_router, prefix=api_prefix)
app.include_router(reviews_router, prefix=api_prefix)
app.include_router(subscription_router, prefix=api_prefix)
app.include_router(support_router, prefix=api_prefix)
app.include_router(search_router, prefix=api_prefix)
app.include_router(events_router, prefix=api_prefix)
app.include_router(signals_router, prefix=api_prefix)
app.include_router(email_ingest_router, prefix=api_prefix)
app.include_router(workflows_router, prefix=api_prefix)
app.include_router(compliance_router, prefix=api_prefix)
app.include_router(compliance_registry_router, prefix=api_prefix)
app.include_router(unanet_router, prefix=api_prefix)
app.include_router(reports_router, prefix=api_prefix)
app.include_router(activity_router, prefix=api_prefix)
app.include_router(intelligence_router, prefix=api_prefix)
app.include_router(admin_router, prefix=api_prefix)
app.include_router(kb_intelligence_router, prefix=api_prefix)
app.include_router(onboarding_router, prefix=api_prefix)
app.include_router(agents_router, prefix=api_prefix)
app.include_router(inbox_router, prefix=api_prefix)
app.include_router(benchmark_router, prefix=api_prefix)


# =============================================================================
# Root Endpoint
# =============================================================================


@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs" if settings.debug else "Disabled in production",
        "health": "/health",
        "metrics": "/metrics" if settings.enable_metrics else "Disabled",
        "api_base": "/api/v1",
    }


@app.get("/metrics", tags=["Observability"])
async def metrics():
    """
    Get application metrics.
    Returns counters, gauges, and histogram summaries.
    """
    if not settings.enable_metrics:
        return JSONResponse(
            status_code=404,
            content={"detail": "Metrics are disabled"},
        )

    metrics_data = get_metrics().get_all()
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.sentry_environment,
        **metrics_data,
    }


# =============================================================================
# Development Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )
