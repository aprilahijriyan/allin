from typing import Optional

from msgspec import ValidationError

from .errors import HTTPError
from .request import Request
from .response import JSONResponse
from .status import status_codes


async def http_error_handler(exc: HTTPError, request: Optional[Request] = None):
    return JSONResponse(exc.to_json(), status_code=exc.code, headers=exc.headers)


async def msgspec_validation_error_handler(
    exc: ValidationError, request: Optional[Request] = None
):
    return JSONResponse({"code": status_codes.UNPROCESSABLE_ENTITY, "detail": str(exc)})


async def internal_server_error_handler(
    exc: Exception, request: Optional[Request] = None
):
    code = status_codes.INTERNAL_SERVER_ERROR
    return JSONResponse({"code": code, "detail": code.phrase})


DEFAULT_ERROR_HANDLERS = {
    HTTPError: http_error_handler,
    ValidationError: msgspec_validation_error_handler,
    Exception: internal_server_error_handler,
}
