# app/main.py

from contextlib import asynccontextmanager
from fastapi import FastAPI
from faststream.kafka import KafkaBroker

from app.core.config import settings
from app.core.logger import setup_logging, get_logger
from app.infrastructure.messaging.broker import broker
from app.api.routes import profile_routes

# Import consumers so their @broker.subscriber decorators register
import app.infrastructure.messaging.consumers.identity_consumer  # noqa: F401

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan: replaces deprecated @app.on_event("startup").

    STARTUP sequence:
    1. Setup logging first (so all subsequent startup logs are structured)
    2. Start Kafka broker (connects to brokers, starts consumers)
    3. Yield (application runs)

    SHUTDOWN sequence (reverse order):
    4. Stop Kafka broker (graceful consumer shutdown, flush producers)

    WHY lifespan over startup/shutdown events?
    lifespan uses async context manager — proper resource management.
    It's the modern FastAPI pattern (FastAPI 0.95+).

    WHY start Kafka in lifespan?
    Kafka connections are expensive. You want ONE persistent connection
    for the lifetime of the process, not per-request connections.
    """
    setup_logging()
    logger.info("profile_service_starting", version=settings.APP_VERSION, env=settings.APP_ENV)

    async with broker:
        logger.info("kafka_broker_connected", servers=settings.KAFKA_BOOTSTRAP_SERVERS)
        yield

    logger.info("profile_service_stopped")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None,   # Hide Swagger in production
    redoc_url=None,
    lifespan=lifespan,
)

# Register routes
app.include_router(profile_routes.router)


@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """
    Liveness probe for Kubernetes / load balancer.
    Returns 200 if the service is running.
    """
    return {"status": "healthy", "service": settings.APP_NAME, "version": settings.APP_VERSION}