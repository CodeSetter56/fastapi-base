import secrets
from typing import Literal, TypedDict, cast

from fastapi import Response

from .config import settings
from .schemas.auth import TokenPair

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
CSRF_COOKIE = "csrf_token"
CSRF_HEADER = "X-CSRF-Token"

UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
CSRF_EXEMPT_PATHS = frozenset({"/auth/login", "/auth/register"})


class _CookieKwargs(TypedDict):
    secure: bool
    samesite: Literal["lax", "strict", "none"] | None


def _common_cookie_kwargs() -> _CookieKwargs:
    return {
        "secure": settings.cookie_secure,
        "samesite": cast(Literal["lax", "strict", "none"] | None, settings.cookie_samesite),
    }


def set_auth_cookies(response: Response, pair: TokenPair) -> None:
    access_max_age = settings.access_token_expire_minutes * 60
    refresh_max_age = settings.refresh_token_expire_days * 24 * 60 * 60

    response.set_cookie(
        ACCESS_COOKIE,
        pair.access_token,
        max_age=access_max_age,
        path="/",
        httponly=True,
        **_common_cookie_kwargs(),
    )
    response.set_cookie(
        REFRESH_COOKIE,
        pair.refresh_token,
        max_age=refresh_max_age,
        path="/auth",
        httponly=True, 
        **_common_cookie_kwargs(),
    )
    response.set_cookie(
        CSRF_COOKIE,
        secrets.token_urlsafe(32),
        max_age=refresh_max_age,
        path="/",
        httponly=False,
        **_common_cookie_kwargs(),
    )


def clear_auth_cookies(response: Response) -> None:
    common = _common_cookie_kwargs()
    response.delete_cookie(ACCESS_COOKIE, path="/", **common)
    response.delete_cookie(REFRESH_COOKIE, path="/auth", **common)
    response.delete_cookie(CSRF_COOKIE, path="/", **common)
