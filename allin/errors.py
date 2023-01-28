from typing import Any

from .status import status_codes


class AllinError(Exception):
    """
    Base class for all exceptions in the Allin framework.
    """


class EndpointError(AllinError):
    """
    Exceptions related to endpoints. This will be thrown in cases like 'endpoint' or 'router' already exists.
    """


class MediaTypeError(AllinError):
    """
    This will be thrown if the 'media type' that the client requested is not what you expected.
    See the `Request._check_media_type` function
    """


class HTTPError(AllinError):
    """
    Exception for providing HTTP responses.
    """

    def __init__(
        self,
        code: int,
        detail: str = None,
        headers: dict[str, Any] = {},  # noqa: B006
        **fields
    ) -> None:
        """
        Args:
            code: HTTP status code
            detail: Description of the HTTP status code. Defaults to None.
            headers: HTTP headers
            \\*\\*fields: Other fields to be merged into the JSON response
        """
        self.code = status_codes(code)
        if detail is None:
            detail = self.code.phrase
        self.detail = detail
        self.headers = headers
        self.fields = fields

    def to_json(self) -> dict:
        return {"code": self.code, "detail": self.detail, **self.fields}


class LostConnection(AllinError):  # noqa: N818
    """
    Exception to handle the client connection with the server is lost.
    """
