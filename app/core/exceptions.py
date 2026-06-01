# app/core/exceptions.py

from fastapi import HTTPException, status


class ProfileNotFoundError(HTTPException):
    """
    Raised when a profile lookup returns no result.

    WHY custom exceptions instead of raw HTTPException everywhere?
    1. Semantic clarity: ProfileNotFoundError tells you exactly
       what went wrong at the business level.
    2. Centralized error codes: Change the HTTP status in one place.
    3. Testability: `except ProfileNotFoundError` is cleaner than
       `except HTTPException` + status code check.

    Spring Boot equivalent: @ResponseStatus(HttpStatus.NOT_FOUND)
    on a custom exception class.
    """

    def __init__(self, identity_id: str) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "PROFILE_NOT_FOUND",
                "message": f"No active profile found for identity: {identity_id}",
            },
        )


class ProfileAlreadyExistsError(HTTPException):
    def __init__(self, identity_id: str) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "PROFILE_ALREADY_EXISTS",
                "message": f"Profile already exists for identity: {identity_id}",
            },
        )


class UnauthorizedError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "UNAUTHORIZED",
                "message": "Valid authentication credentials are required.",
            },
        )