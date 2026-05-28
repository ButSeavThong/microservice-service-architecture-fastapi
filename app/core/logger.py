# app/core/logger.py

import logging
import structlog
from app.core.config import settings


def setup_logging() -> None:
    """
    Configure structlog for structured JSON logging.

    WHY structured logging?
    In production, logs go to Elasticsearch, Loki, or CloudWatch.
    These systems index JSON fields — you can query:
      - "all errors from profile-service in the last 5 minutes"
      - "all requests for identity_id=user-123"
      - "p99 latency for GET /profiles"

    With print() or unstructured logging, you can't do this.
    You're flying blind.

    WHY structlog over standard logging?
    - Automatic context binding (add identity_id once, it appears in all logs)
    - Consistent key=value output
    - Works beautifully with OpenTelemetry trace IDs
    """

    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    # Configure standard library logging (for third-party libraries)
    logging.basicConfig(
        format="%(message)s",
        level=log_level,
    )

    # Choose renderer based on environment
    if settings.APP_ENV == "production":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,         # Thread-safe context
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Returns a bound logger instance for a given module.

    Usage:
        logger = get_logger(__name__)
        logger.info("profile_created", identity_id="user-123", profile_id="abc")

    Output (production JSON):
        {
          "level": "info",
          "event": "profile_created",
          "identity_id": "user-123",
          "profile_id": "abc",
          "timestamp": "2024-01-15T10:30:00Z",
          "logger": "app.services.profile_service"
        }
    """
    return structlog.get_logger(name)