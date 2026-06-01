# Shared configuration

# app/core/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """
    Centralised configuration using Pydantic Settings.

    Reads from environment variables or .env file.
    In production: inject via Kubernetes Secrets or Docker env.
    In development: use .env file.

    WHY Pydantic Settings?
    - Type-safe: if DATABASE_URL is missing, it fails at startup — not at runtime.
    - No scattered os.getenv() calls across your codebase.
    - One single source of truth.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Application ──────────────────────────────────────────
    APP_NAME: str = "profile-service"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"       # development | staging | production
    DEBUG: bool = False

    # ── Database ──────────────────────────────────────────────
    DATABASE_URL: str                  # postgresql+asyncpg://user:pass@host/db
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_ECHO: bool = False        # Set True only for local SQL debugging

    # ── Kafka ─────────────────────────────────────────────────
    KAFKA_BOOTSTRAP_SERVERS: str       # "kafka:9092" or "broker1:9092,broker2:9092"
    KAFKA_CONSUMER_GROUP: str = "profile-service-group"

    # Kafka Topics (consumed)
    KAFKA_TOPIC_IDENTITY_USER_CREATED: str = "identity.user.created"

    # Kafka Topics (produced)
    KAFKA_TOPIC_PROFILE_CREATED: str = "profile.profile.created"
    KAFKA_TOPIC_PROFILE_UPDATED: str = "profile.profile.updated"

    # ── Valkey / Redis ────────────────────────────────────────
    VALKEY_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 300       # 5 minutes default TTL

    # ── JWT ───────────────────────────────────────────────────
    # We do NOT validate JWT here — WSO2 Gateway already did.
    # We only decode claims. But we store the issuer for
    # optional secondary verification in high-security paths.
    JWT_ISSUER: str = "https://localhost:9443/oauth2/token"

    # ── Observability ─────────────────────────────────────────
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://otel-collector:4317"
    OTEL_SERVICE_NAME: str = "profile-service"

    # ── Correlation ───────────────────────────────────────────
    CORRELATION_ID_HEADER: str = "X-Correlation-ID"


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.

    WHY lru_cache?
    Without caching, every call to get_settings() would re-read
    the .env file and re-validate. With lru_cache, we read once
    at startup and reuse the same object.

    In FastAPI dependency injection, this gets called per-request
    if you inject it directly — lru_cache prevents that overhead.
    """
    return Settings()


# Module-level singleton for non-DI contexts (e.g., Alembic env.py)
settings = get_settings()