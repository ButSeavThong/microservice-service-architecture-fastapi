# app/api/dependencies/auth.py

from typing import Annotated
from fastapi import Depends, Header
from jose import jwt, JWTError

from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.core.logger import get_logger

logger = get_logger(__name__)


class JWTClaims:
    """
    Represents the verified claims extracted from the JWT.

    WHY a class instead of a dict?
    Type safety. When you access claims.identity_id, your IDE
    knows the type and flags mistakes at development time.
    A dict['sub'] fails silently until runtime.
    """

    def __init__(self, identity_id: str, email: str, roles: list[str]) -> None:
        self.identity_id = identity_id
        self.email = email
        self.roles = roles


async def get_current_user(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> JWTClaims:
    """
    FastAPI dependency that extracts identity from the JWT.

    IMPORTANT ARCHITECTURAL NOTE:
    We are NOT validating the JWT signature here.
    WSO2 API Gateway already validated it before forwarding the request.
    We are only DECODING the payload to read claims.

    WHY decode at all if Gateway validated?
    The Gateway strips/forwards the JWT but your service needs
    the identity_id (sub) to know WHOSE profile to fetch.
    You can't know that without reading the token.

    SECURITY NOTE:
    This only works if your service is ONLY accessible through
    the Gateway. If someone can call profile-service directly
    (bypassing Gateway), they could forge tokens.

    In production: profile-service should be in a private network
    segment (VPC/namespace) unreachable from the public internet.
    Only the Gateway has network access to it.

    In high-security scenarios: add secondary JWT signature
    verification using WSO2's JWKS endpoint.
    """
    if not authorization:
        raise UnauthorizedError()

    # Header format: "Bearer <token>"
    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise UnauthorizedError()

    token = parts[1]

    try:
        # options={"verify_signature": False} because Gateway already verified.
        # We trust the Gateway — this is a zero-trust-within-network design.
        payload = jwt.decode(
            token,
            key="",
            options={
                "verify_signature": False,
                "verify_exp": False,   # Gateway enforces expiry
                "verify_aud": False,
            },
            algorithms=["RS256"],
        )
    except JWTError as e:
        logger.warning("jwt_decode_failed", error=str(e))
        raise UnauthorizedError()

    identity_id = payload.get("sub")
    email = payload.get("email", "")
    roles = payload.get("roles", [])

    if not identity_id:
        logger.warning("jwt_missing_sub_claim")
        raise UnauthorizedError()

    return JWTClaims(
        identity_id=identity_id,
        email=email,
        roles=roles,
    )


# Typed alias for use in route signatures
CurrentUser = Annotated[JWTClaims, Depends(get_current_user)]