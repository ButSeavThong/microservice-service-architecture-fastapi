# app/core/logger.py

import logging
import structlog
from app.core.config import settings


def setup_logging() -> None:
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    logging.basicConfig(format="%(message)s", level=log_level)

    # Suppress noisy third-party loggers
    logging.getLogger("aiokafka").setLevel(logging.WARNING)
    logging.getLogger("kafka").setLevel(logging.WARNING)
    logging.getLogger("faststream").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    renderer = (
        structlog.dev.ConsoleRenderer(colors=True)
        if settings.APP_ENV != "production"
        else structlog.processors.JSONRenderer()
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    return structlog.get_logger(name)