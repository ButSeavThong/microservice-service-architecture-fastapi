from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import profile_routes
from app.core.config import settings
from app.core.logger import get_logger, setup_logging
from app.infrastructure.messaging.broker import broker

# IMPORTANT:
# Import consumers so decorators execute
from app.infrastructure.messaging.consumers import identity_consumer  # noqa: F401

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()

    logger.info(
        "profile_service_starting",
        version=settings.APP_VERSION,
        env=settings.APP_ENV,
    )

    logger.info(
        "kafka_configuration",
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        topic=settings.KAFKA_TOPIC_IDENTITY_USER_CREATED,
        consumer_group=settings.KAFKA_CONSUMER_GROUP,
    )

    try:
        async with broker:
            logger.info(
                "kafka_broker_started",
                servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            )

            yield

    except Exception:
        logger.exception("kafka_broker_failed")
        raise

    finally:
        logger.info("profile_service_stopped")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url=None,
    lifespan=lifespan,
)

app.include_router(profile_routes.router)


@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }