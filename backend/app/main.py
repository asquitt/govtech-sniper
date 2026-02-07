"""
RFP Sniper - FastAPI Application Entry Point
=============================================
The main application that ties everything together.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from app.config import settings
from app.database import init_db, close_db
from app.observability import (
    init_sentry,
    setup_logging,
    get_logger,
    MetricsMiddleware,
)
from app.observability.logging import RequestLoggingMiddleware, CorrelationIDMiddleware
from app.observability.sentry import capture_exception
from app.observability.metrics import get_metrics
from app.api.routes import (
    ingest_router,
    analyze_router,
    draft_router,
    rfps_router,
    documents_router,
    health_router,
    auth_router,
    websocket_router,
    analytics_router,
    templates_router,
    export_router,
    notifications_router,
    teams_router,
    versions_router,
    integrations_router,
    webhooks_router,
    dash_router,
    capture_router,
    contracts_router,
    audit_router,
    saved_searches_router,
    awards_router,
    contacts_router,
    word_addin_router,
    graphics_router,
    scim_router,
    secrets_router,
    budget_intel_router,
    revenue_router,
    capture_timeline_router,
    forecasts_router,
    teaming_board_router,
    collaboration_router,
    sharepoint_router,
    salesforce_router,
    data_sources_router,
    analytics_reporting_router,
    reviews_router,
    subscription_router,
    search_router,
    events_router,
    signals_router,
    email_ingest_router,
    workflows_router,
    compliance_router,
)

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

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://localhost:8000",
        "http://127.0.0.1:3000",
    ],
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
    error_id = capture_exception(exc, context={
        "path": request.url.path,
        "method": request.method,
        "query_params": str(request.query_params),
    })

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

# Protected routes
app.include_router(ingest_router, prefix=api_prefix)
app.include_router(analyze_router, prefix=api_prefix)
app.include_router(draft_router, prefix=api_prefix)
app.include_router(rfps_router, prefix=api_prefix)
app.include_router(documents_router, prefix=api_prefix)
app.include_router(export_router, prefix=api_prefix)
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
app.include_router(salesforce_router, prefix=api_prefix)
app.include_router(data_sources_router, prefix=api_prefix)
app.include_router(analytics_reporting_router, prefix=api_prefix)
app.include_router(reviews_router, prefix=api_prefix)
app.include_router(subscription_router, prefix=api_prefix)
app.include_router(search_router, prefix=api_prefix)
app.include_router(events_router, prefix=api_prefix)
app.include_router(signals_router, prefix=api_prefix)
app.include_router(email_ingest_router, prefix=api_prefix)
app.include_router(workflows_router, prefix=api_prefix)
app.include_router(compliance_router, prefix=api_prefix)


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
