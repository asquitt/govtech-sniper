"""
RFP Sniper - Structured Logging
===============================
Production-ready structured logging with structlog.
"""

import logging
import sys

import structlog


def setup_logging(
    log_level: str = "INFO",
    json_format: bool = True,
    include_timestamps: bool = True,
) -> None:
    """
    Configure structured logging for the application.

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR)
        json_format: If True, output JSON logs (production). If False, pretty-print (development)
        include_timestamps: Include ISO timestamps in logs
    """
    # Convert string level to logging constant
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )

    # Common processors for all environments
    shared_processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso")
        if include_timestamps
        else lambda *args, **kwargs: args[2],
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if json_format:
        # Production: JSON output for log aggregators
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Development: Pretty-printed colored output
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        A bound structlog logger
    """
    return structlog.get_logger(name)


class RequestLoggingMiddleware:
    """
    Middleware for logging HTTP requests with structured data.
    """

    def __init__(self, app, logger: structlog.BoundLogger | None = None):
        self.app = app
        self.logger = logger or get_logger("http")

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        import time

        from starlette.requests import Request

        request = Request(scope)
        start_time = time.perf_counter()

        # Store response status for logging
        response_status = 500

        async def send_wrapper(message):
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            self.logger.error(
                "Request failed with exception",
                method=request.method,
                path=request.url.path,
                error=str(exc),
                exc_info=True,
            )
            raise
        finally:
            process_time = time.perf_counter() - start_time

            # Log successful requests at info level, errors at warning/error
            log_method = self.logger.info
            if response_status >= 500:
                log_method = self.logger.error
            elif response_status >= 400:
                log_method = self.logger.warning

            log_method(
                "Request completed",
                method=request.method,
                path=request.url.path,
                status=response_status,
                duration_ms=round(process_time * 1000, 2),
                client_ip=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent", "")[:100],
            )


class CorrelationIDMiddleware:
    """
    Middleware to add correlation IDs for request tracing.
    """

    def __init__(self, app, header_name: str = "X-Correlation-ID"):
        self.app = app
        self.header_name = header_name

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        import uuid

        from starlette.requests import Request

        request = Request(scope)

        # Get or generate correlation ID
        correlation_id = request.headers.get(self.header_name)
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        # Bind to structlog context
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        # Add correlation ID to response headers
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((self.header_name.lower().encode(), correlation_id.encode()))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            structlog.contextvars.unbind_contextvars("correlation_id")
