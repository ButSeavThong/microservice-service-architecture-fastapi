# app/infrastructure/cache/valkey_client.py

import json
from typing import Annotated

import redis.asyncio as redis
from fastapi import Depends

from app.core.config import settings
from app.core.logger import get_logger
from app.schemas.profile_schema import ProfileResponse

logger = get_logger(__name__)

# Module-level connection pool (shared across all requests)
_redis_pool = redis.ConnectionPool.from_url(
    settings.VALKEY_URL,
    max_connections=20,
    decode_responses=True,
)


def get_valkey_client() -> redis.Redis:
    return redis.Redis(connection_pool=_redis_pool)


class ProfileCache:
    """
    Valkey (Redis-compatible) cache for Profile data.

    Cache key pattern: "profile:v1:{identity_id}"

    WHY include version in key?
    When you change the ProfileResponse schema, cached data
    with the old shape would cause Pydantic parse errors.
    Bump "v1" → "v2" to instantly invalidate all old cache entries.

    WHY cache by identity_id and not profile_id?
    Every request comes in with identity_id (from JWT).
    If you cache by profile_id, you'd need a DB query to find
    the profile_id from identity_id first — defeating the purpose.
    """

    CACHE_KEY_PREFIX = "profile:v1:"

    def __init__(self, client: redis.Redis | None = None) -> None:
        self._client = client or get_valkey_client()

    def _key(self, identity_id: str) -> str:
        return f"{self.CACHE_KEY_PREFIX}{identity_id}"

    async def get_profile(self, identity_id: str) -> ProfileResponse | None:
        try:
            data = await self._client.get(self._key(identity_id))
            if data:
                return ProfileResponse.model_validate_json(data)
            return None
        except Exception as e:
            # Cache failures must NEVER break the main request flow.
            # Log and fall through to DB.
            logger.warning("cache_get_failed", error=str(e), identity_id=identity_id)
            return None

    async def set_profile(self, identity_id: str, profile: ProfileResponse) -> None:
        try:
            await self._client.setex(
                name=self._key(identity_id),
                time=settings.CACHE_TTL_SECONDS,
                value=profile.model_dump_json(),
            )
        except Exception as e:
            logger.warning("cache_set_failed", error=str(e), identity_id=identity_id)

    async def delete_profile(self, identity_id: str) -> None:
        try:
            await self._client.delete(self._key(identity_id))
        except Exception as e:
            logger.warning("cache_delete_failed", error=str(e), identity_id=identity_id)


async def get_profile_cache() -> ProfileCache:
    return ProfileCache(client=get_valkey_client())