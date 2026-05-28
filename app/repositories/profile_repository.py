# app/repositories/profile_repository.py

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.models.profile import Profile

logger = get_logger(__name__)


class ProfileRepository:
    """
    Data access layer for Profile entities.

    RESPONSIBILITIES:
    - All SQL queries for Profile
    - No business logic here — only data access
    - No HTTP concerns
    - No event publishing

    WHY a repository class (not module-level functions)?
    1. Testability: You can mock/stub the entire repository in service tests.
    2. Consistency: All Profile DB operations live in one place.
    3. Replaceability: If you switch from PostgreSQL to MongoDB,
       only this class changes — service layer is untouched.

    Spring Boot equivalent: This is your JpaRepository / custom
    @Repository interface implementation.

    IMPORTANT: The repository receives a session as a parameter.
    It does NOT own or manage the session lifecycle.
    Session lifecycle is managed by:
    - get_db_session() dependency for HTTP requests
    - get_session_context() for Kafka consumers

    WHY pass session as parameter?
    So the service layer can control transaction boundaries.
    If a service operation involves multiple repository calls,
    they all share one session/transaction — atomicity guaranteed.
    """

    async def create(self, session: AsyncSession, profile: Profile) -> Profile:
        """
        Persist a new Profile to the database.

        We use session.add() + flush() pattern:
        - add(): Registers object with the session (no DB call yet)
        - flush(): Writes to DB within the transaction (no commit yet)
        - refresh(): Reloads the object to get DB-generated values

        WHY flush instead of commit here?
        The repository should NOT commit. Commit is the service layer's
        decision. This allows the service to:
        1. Create a profile
        2. Publish an event
        3. Commit both atomically (or roll back both)
        """
        session.add(profile)
        await session.flush()
        await session.refresh(profile)

        logger.debug(
            "profile_persisted",
            profile_id=profile.id,
            identity_id=profile.identity_id,
        )
        return profile

    async def get_by_id(self, session: AsyncSession, profile_id: str) -> Profile | None:
        """
        Fetch a profile by its primary key.
        Returns None if not found (caller decides how to handle).
        """
        stmt = select(Profile).where(
            Profile.id == profile_id,
            Profile.is_active == True,  # noqa: E712
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_identity_id(
        self, session: AsyncSession, identity_id: str
    ) -> Profile | None:
        """
        Fetch a profile by identity_id (JWT `sub` claim).

        This is the most common query in this service.
        WHY index on identity_id?
        Without an index, PostgreSQL does a full table scan.
        At 1M profiles, that's 1M rows checked per request.
        With an index, it's O(log n) — ~20 comparisons.
        """
        stmt = select(Profile).where(
            Profile.identity_id == identity_id,
            Profile.is_active == True,  # noqa: E712
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(
        self,
        session: AsyncSession,
        profile: Profile,
        update_data: dict,
    ) -> Profile:
        """
        Update a Profile with a dictionary of field changes.

        WHY dict-based updates?
        Allows partial updates (PATCH semantics).
        If the client only sends display_name, only display_name changes.
        We don't accidentally null out other fields.

        Implementation note:
        We update the ORM object directly, not with UPDATE SQL.
        This keeps the object in the session's identity map — consistent.
        """
        for field, value in update_data.items():
            setattr(profile, field, value)

        await session.flush()
        await session.refresh(profile)

        logger.debug(
            "profile_updated",
            profile_id=profile.id,
            updated_fields=list(update_data.keys()),
        )
        return profile

    async def soft_delete(self, session: AsyncSession, profile: Profile) -> Profile:
        """
        Deactivate a profile (soft delete).

        NEVER hard-delete in production unless legally required (GDPR).
        Soft delete = set is_active=False.

        WHY?
        - Other services may reference this profile_id
        - You need audit trails
        - Account recovery becomes possible
        - Analytics remain intact
        """
        profile.is_active = False
        await session.flush()
        return profile