# app/services/profile_service.py

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.core.exceptions import ProfileNotFoundError, ProfileAlreadyExistsError
from app.infrastructure.messaging.broker import broker
from app.infrastructure.cache.valkey_client import ProfileCache
from app.models.profile import Profile
from app.repositories.profile_repository import ProfileRepository
from app.schemas.events.profile_events import ProfileCreatedEvent, ProfileUpdatedEvent
from app.schemas.profile_schema import ProfileResponse, ProfileUpdateRequest
from app.core.config import settings

logger = get_logger(__name__)


class ProfileService:
    """
    The business logic layer for Profile operations.

    RESPONSIBILITIES:
    - Orchestrate repository calls
    - Own transaction boundaries (when to commit)
    - Publish domain events after successful changes
    - Invalidate/update cache
    - Log meaningful business events (not just technical events)

    DOES NOT:
    - Write SQL (repository does that)
    - Handle HTTP concerns (routes do that)
    - Know about Kafka topics directly (uses publishers)

    WHY inject repository and cache?
    Testability. In unit tests, you inject mock versions.
    Your service logic is tested without a real DB or cache.

    Spring Boot equivalent:
    This is your @Service class. The repository is your
    @Autowired JpaRepository. The session is your @Transactional
    boundary.
    """

    def __init__(
        self,
        profile_repo: ProfileRepository,
        cache: ProfileCache,
    ) -> None:
        self.profile_repo = profile_repo
        self.cache = cache

    async def create_profile_from_identity_event(
        self,
        session: AsyncSession,
        identity_id: str,
        email: str,
    ) -> Profile:
        """
        Called by the Kafka consumer when identity.user.created fires.

        FLOW:
        1. Check if profile already exists (idempotency guard)
        2. Create Profile ORM object
        3. Persist via repository (flush, no commit yet)
        4. Publish ProfileCreatedEvent to Kafka
        5. Commit transaction
        6. Return profile

        WHY check for existing profile first?
        Kafka guarantees at-least-once delivery.
        The same event MAY arrive twice (e.g., consumer crash mid-process).
        Without this check, you'd create duplicate profiles.
        This is called IDEMPOTENCY — applying the same operation
        multiple times has the same result as applying it once.
        """
        existing = await self.profile_repo.get_by_identity_id(session, identity_id)
        if existing:
            logger.warning(
                "profile_already_exists_skipping",
                identity_id=identity_id,
                profile_id=existing.id,
            )
            return existing

        profile = Profile(
            identity_id=identity_id,
            email=email,
        )

        profile = await self.profile_repo.create(session, profile)

        # Publish event BEFORE commit (if publish fails, we rollback everything)
        await broker.publish(
            ProfileCreatedEvent(
                event_id=str(uuid.uuid4()),
                profile_id=profile.id,
                identity_id=identity_id,
                email=email,
                occurred_at=datetime.now(timezone.utc),
            ),
            topic=settings.KAFKA_TOPIC_PROFILE_CREATED,
        )

        await session.commit()
        
        # ✅ Populate cache AFTER commit — data is fully persisted
        response = ProfileResponse.model_validate(profile)
        await self.cache.set_profile(identity_id, response)

        logger.info(
            "profile_created",
            profile_id=profile.id,
            identity_id=identity_id,
        )

        return profile

    async def get_my_profile(
        self,
        session: AsyncSession,
        identity_id: str,
    ) -> ProfileResponse:
        """
        Retrieve the authenticated user's own profile.

        FLOW:
        1. Check Valkey cache first
        2. On cache miss: query DB
        3. Store in cache
        4. Return

        WHY cache profiles?
        GET /me is called on every page load in most apps.
        At 10,000 concurrent users, that's 10,000 DB queries/second.
        With caching: most served from Valkey in <1ms.
        DB load drops dramatically.
        """
        # 1. Cache check
        cached = await self.cache.get_profile(identity_id)
        if cached:
            logger.debug("profile_cache_hit", identity_id=identity_id)
            return cached

        # 2. DB query
        profile = await self.profile_repo.get_by_identity_id(session, identity_id)
        if not profile:
            raise ProfileNotFoundError(identity_id=identity_id)

        response = ProfileResponse.model_validate(profile)

        # 3. Populate cache
        await self.cache.set_profile(identity_id, response)

        return response

    async def update_my_profile(
        self,
        session: AsyncSession,
        identity_id: str,
        update_request: ProfileUpdateRequest,
    ) -> ProfileResponse:
        """
        Update the authenticated user's profile.

        FLOW:
        1. Fetch current profile
        2. Compute changed fields (for event payload)
        3. Apply updates via repository
        4. Invalidate cache (stale data must go)
        5. Publish ProfileUpdatedEvent
        6. Commit
        7. Return updated profile
        """
        profile = await self.profile_repo.get_by_identity_id(session, identity_id)
        if not profile:
            raise ProfileNotFoundError(identity_id=identity_id)

        # Only update fields that were explicitly provided
        update_data = update_request.model_dump(exclude_unset=True, exclude_none=False)

        if not update_data:
            # Nothing to update — return current profile
            return ProfileResponse.model_validate(profile)

        profile = await self.profile_repo.update(session, profile, update_data)

        # Invalidate stale cache immediately
        await self.cache.delete_profile(identity_id)

        # Publish update event
        await broker.publish(
            ProfileUpdatedEvent(
                event_id=str(uuid.uuid4()),
                profile_id=profile.id,
                identity_id=identity_id,
                changed_fields=list(update_data.keys()),
                occurred_at=datetime.now(timezone.utc),
            ),
            topic=settings.KAFKA_TOPIC_PROFILE_UPDATED,
        )

        await session.commit()

        logger.info(
            "profile_updated",
            profile_id=profile.id,
            identity_id=identity_id,
            changed_fields=list(update_data.keys()),
        )

        return ProfileResponse.model_validate(profile)