"""
RFP Sniper - Sentry Integration
===============================
Error tracking and performance monitoring with Sentry.
"""

import structlog

logger = structlog.get_logger(__name__)


def init_sentry(
    dsn: str | None,
    environment: str = "development",
    traces_sample_rate: float = 0.1,
    release: str | None = None,
) -> bool:
    """
    Initialize Sentry SDK for error tracking.

    Args:
        dsn: Sentry DSN (if None, Sentry is disabled)
        environment: Environment name (development, staging, production)
        traces_sample_rate: Sample rate for performance tracing (0.0 to 1.0)
        release: Application release/version string

    Returns:
        True if Sentry was initialized, False otherwise
    """
    if not dsn:
        logger.info("Sentry DSN not configured, error tracking disabled")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.httpx import HttpxIntegration
        from sentry_sdk.integrations.redis import RedisIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            traces_sample_rate=traces_sample_rate,
            release=release,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
                RedisIntegration(),
                HttpxIntegration(),
            ],
            # Don't send PII by default
            send_default_pii=False,
            # Capture failed requests
            failed_request_status_codes={400, 401, 403, 404, 405, 500, 502, 503, 504},
            # Filter sensitive data
            before_send=_before_send,
        )

        logger.info(
            "Sentry initialized",
            environment=environment,
            traces_sample_rate=traces_sample_rate,
        )
        return True

    except ImportError:
        logger.warning("sentry-sdk not installed, error tracking disabled")
        return False
    except Exception as e:
        logger.error("Failed to initialize Sentry", error=str(e))
        return False


def _before_send(event, hint):
    """
    Filter sensitive data before sending to Sentry.
    """
    # Remove sensitive headers
    if "request" in event and "headers" in event["request"]:
        sensitive_headers = ["authorization", "cookie", "x-api-key"]
        for header in sensitive_headers:
            if header in event["request"]["headers"]:
                event["request"]["headers"][header] = "[Filtered]"

    # Remove sensitive query params
    if "request" in event and "query_string" in event["request"]:
        query = event["request"].get("query_string", "")
        if "api_key" in query or "token" in query:
            event["request"]["query_string"] = "[Filtered]"

    return event


def capture_exception(exc: Exception, context: dict | None = None) -> str | None:
    """
    Manually capture an exception and send to Sentry.

    Args:
        exc: The exception to capture
        context: Additional context to attach to the error

    Returns:
        The Sentry event ID if sent, None otherwise
    """
    try:
        import sentry_sdk

        with sentry_sdk.push_scope() as scope:
            if context:
                for key, value in context.items():
                    scope.set_extra(key, value)
            return sentry_sdk.capture_exception(exc)
    except ImportError:
        return None


def capture_message(message: str, level: str = "info", context: dict | None = None) -> str | None:
    """
    Capture a message and send to Sentry.

    Args:
        message: The message to capture
        level: Severity level (debug, info, warning, error, fatal)
        context: Additional context to attach

    Returns:
        The Sentry event ID if sent, None otherwise
    """
    try:
        import sentry_sdk

        with sentry_sdk.push_scope() as scope:
            if context:
                for key, value in context.items():
                    scope.set_extra(key, value)
            return sentry_sdk.capture_message(message, level=level)
    except ImportError:
        return None


def set_user(user_id: int, email: str | None = None, username: str | None = None):
    """
    Set the current user context for Sentry.

    Args:
        user_id: User's unique identifier
        email: User's email (optional)
        username: User's username (optional)
    """
    try:
        import sentry_sdk

        sentry_sdk.set_user(
            {
                "id": user_id,
                "email": email,
                "username": username,
            }
        )
    except ImportError:
        pass


def add_breadcrumb(
    message: str,
    category: str = "custom",
    level: str = "info",
    data: dict | None = None,
):
    """
    Add a breadcrumb for debugging.

    Args:
        message: Breadcrumb message
        category: Category for grouping
        level: Severity level
        data: Additional data
    """
    try:
        import sentry_sdk

        sentry_sdk.add_breadcrumb(
            message=message,
            category=category,
            level=level,
            data=data or {},
        )
    except ImportError:
        pass
