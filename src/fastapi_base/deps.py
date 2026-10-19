from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from .cookies import ACCESS_COOKIE
from .db import get_session
from .models import User, UserRole
from .security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(detail: str = "Could not validate credentials") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_session),
) -> User:
    # An explicit Authorization header wins; otherwise fall back to the cookie.
    token = (
        credentials.credentials
        if credentials is not None
        else request.cookies.get(ACCESS_COOKIE)
    )
    if token is None:
        raise _unauthorized("Not authenticated")

    try:
        claims = decode_token(token)
    except InvalidTokenError:
        raise _unauthorized() from None

    if claims.get("type") != "access":
        raise _unauthorized()

    try:
        user_id = UUID(claims["sub"])
    except (TypeError, ValueError):
        raise _unauthorized() from None

    user = await db.get(User, user_id)
    if user is None:
        raise _unauthorized()
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    if claims.get("ver") != user.token_version:
        raise _unauthorized("Token is no longer valid")

    return user


async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user
