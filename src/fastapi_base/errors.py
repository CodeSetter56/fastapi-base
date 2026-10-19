import logging
from collections.abc import Mapping
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

_ERROR_CODES = {
    HTTPStatus.BAD_REQUEST.value: "bad_request",
    HTTPStatus.UNAUTHORIZED.value: "unauthorized",
    HTTPStatus.FORBIDDEN.value: "forbidden",
    HTTPStatus.NOT_FOUND.value: "not_found",
    HTTPStatus.METHOD_NOT_ALLOWED.value: "method_not_allowed",
    HTTPStatus.CONFLICT.value: "conflict",
    HTTPStatus.UNPROCESSABLE_ENTITY.value: "validation_error",
    HTTPStatus.TOO_MANY_REQUESTS.value: "too_many_requests",
    HTTPStatus.INTERNAL_SERVER_ERROR.value: "internal_error",
}


def error_response(
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, str]] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    error: dict[str, object] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return JSONResponse(
        status_code=status_code,
        content={"error": error},
        headers=headers,
    )


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        _request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        code = _ERROR_CODES.get(exc.status_code, "http_error")
        message = exc.detail if isinstance(exc.detail, str) else "Request failed"
        return error_response(exc.status_code, code, message, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        details = [
            {
                "field": ".".join(str(part) for part in error["loc"][1:]) or "body",
                "message": error["msg"],
                "type": error["type"],
            }
            for error in exc.errors()
        ]
        return error_response(
            HTTPStatus.UNPROCESSABLE_ENTITY.value,
            "validation_error",
            "Request validation failed",
            details=details,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(
        _request: Request,
        _exc: Exception,
    ) -> JSONResponse:
        logger.exception("Unhandled error")
        return error_response(
            HTTPStatus.INTERNAL_SERVER_ERROR.value,
            "internal_error",
            "Internal server error",
        )
