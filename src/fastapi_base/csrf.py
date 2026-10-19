import hmac

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from .cookies import (
    ACCESS_COOKIE,
    CSRF_COOKIE,
    CSRF_EXEMPT_PATHS,
    CSRF_HEADER,
    REFRESH_COOKIE,
    UNSAFE_METHODS,
)
from .errors import error_response


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        path = request.url.path.rstrip("/") or "/"
        uses_cookies = (
            ACCESS_COOKIE in request.cookies or REFRESH_COOKIE in request.cookies
        )
        needs_check = (
            request.method in UNSAFE_METHODS
            and path not in CSRF_EXEMPT_PATHS
            and uses_cookies
            and "authorization" not in request.headers
        )

        if needs_check:
            cookie_token = request.cookies.get(CSRF_COOKIE, "")
            header_token = request.headers.get(CSRF_HEADER, "")
            if not cookie_token or not hmac.compare_digest(
                header_token.encode("utf-8"),
                cookie_token.encode("utf-8"),
            ):
                return error_response(
                    403,
                    "csrf_failed",
                    "Missing or invalid CSRF token",
                )

        return await call_next(request)
