# app/api/v1/routes/profile_routes.py

from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import CurrentUser
from app.db.session import get_db_session
from app.infrastructure.cache.valkey_client import get_profile_cache, ProfileCache
from app.repositories.profile_repository import ProfileRepository
from app.schemas.profile_schema import ProfileResponse, ProfileUpdateRequest
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/v1/profiles", tags=["Profiles"])


def get_profile_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    cache: Annotated[ProfileCache, Depends(get_profile_cache)],
) -> ProfileService:
    """
    Dependency factory: builds ProfileService with its dependencies.

    WHY not inject ProfileService directly?
    ProfileService needs a session and cache injected.
    FastAPI's DI system resolves this tree automatically:
    - get_db_session() → AsyncSession
    - get_profile_cache() → ProfileCache
    - Both injected into ProfileService

    This is equivalent to Spring's @Autowired constructor injection.
    """
    return ProfileService(
        profile_repo=ProfileRepository(),
        cache=cache,
    )


ProfileServiceDep = Annotated[ProfileService, Depends(get_profile_service)]
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("/me", response_model=ProfileResponse, summary="Get my profile")
async def get_my_profile(
    current_user: CurrentUser,
    service: ProfileServiceDep,
    session: DbSession,
) -> ProfileResponse:
    """
    Retrieve the authenticated user's profile.

    Note: `current_user` is populated by the JWT dependency.
    The route does NOT know about SQL, Kafka, or Redis.
    It delegates entirely to the service layer.

    This is the Single Responsibility Principle at the HTTP layer.
    """
    return await service.get_my_profile(session, current_user.identity_id)


@router.patch("/me", response_model=ProfileResponse, summary="Update my profile")
async def update_my_profile(
    current_user: CurrentUser,
    update_request: ProfileUpdateRequest,
    service: ProfileServiceDep,
    session: DbSession,
) -> ProfileResponse:
    """
    Partially update the authenticated user's profile.

    WHY PATCH and not PUT?
    PUT = replace entire resource (send all fields)
    PATCH = partial update (send only changed fields)

    For profile updates, users change one field at a time.
    PATCH is semantically correct and prevents accidental
    nulling of fields the client didn't send.
    """
    return await service.update_my_profile(
        session, current_user.identity_id, update_request
    )