from datetime import datetime
from typing import Any, Callable, Literal, Optional, Union

from asgi_typing import ASGISendCallable
from biscuits import Cookie
from msgspec import json, msgpack

from .status import status_codes

SAMESITE_COOKIE_VALUES = Literal["strict", "lax", "none"]


class Response:
    """
    A class for wrapping and sending responses to the client side.
    This is the original of the Starlette Response object.

    See: https://github.com/encode/starlette/blob/master/starlette/responses.py#L38
    """

    charset = "utf-8"
    media_type = "text/plain"  # default content type

    def __init__(
        self,
        content: Any,
        *,
        status_code: Union[int, status_codes] = 200,
        headers: dict[str, Any] = None,
        media_type: Optional[str] = None,
    ) -> None:
        self.status_code = status_code
        if media_type is not None:
            self.media_type = media_type

        self.body = self.render(content)
        self.raw_headers = self.init_headers(headers)

    def render(self, content: Any) -> bytes:
        if content is None:
            return b""
        if isinstance(content, bytes):
            return content
        return content.encode(self.charset)

    def init_headers(
        self, headers: Optional[dict[str, str]] = None
    ) -> list[tuple[bytes, bytes]]:
        if headers is None:
            raw_headers: list[tuple[bytes, bytes]] = []
            populate_content_length = True
            populate_content_type = True
        else:
            raw_headers = [
                (k.lower().encode("latin-1"), v.encode("latin-1"))
                for k, v in headers.items()
            ]
            keys = [h[0] for h in raw_headers]
            populate_content_length = b"content-length" not in keys
            populate_content_type = b"content-type" not in keys

        body = getattr(self, "body", None)
        if (
            body is not None
            and populate_content_length
            and not (self.status_code < 200 or self.status_code in (204, 304))
        ):
            content_length = str(len(body))
            raw_headers.append((b"content-length", content_length.encode("latin-1")))

        content_type = self.media_type
        if content_type is not None and populate_content_type:
            if content_type.startswith("text/"):
                content_type += "; charset=" + self.charset
            raw_headers.append((b"content-type", content_type.encode("latin-1")))

        return raw_headers

    def set_cookie(
        self,
        name: str,
        value: str,
        path: str = "/",
        domain: Optional[str] = None,
        secure: bool = False,
        httponly: bool = False,
        max_age: int = 0,
        expires: datetime = None,
        samesite: Optional[SAMESITE_COOKIE_VALUES] = "lax",
    ):
        if samesite is not None and samesite not in SAMESITE_COOKIE_VALUES.__args__:
            raise ValueError(
                f"the 'samesite' cookie value must be {SAMESITE_COOKIE_VALUES.__args__}"
            )
        cookie = str(
            Cookie(
                name,
                value,
                path=path,
                domain=domain,
                secure=secure,
                httponly=httponly,
                max_age=max_age,
                expires=expires,
                samesite=samesite,
            )
        )
        self.raw_headers.append((b"set-cookie", cookie.encode("latin-1")))

    def delete_cookie(
        self,
        name: str,
        path: str = "/",
        domain: Optional[str] = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: Optional[SAMESITE_COOKIE_VALUES] = "lax",
    ):
        self.set_cookie(
            name,
            max_age=0,
            expires=0,
            path=path,
            domain=domain,
            secure=secure,
            httponly=httponly,
            samesite=samesite,
        )

    async def __call__(self, send: ASGISendCallable) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": int(self.status_code),
                "headers": self.raw_headers,
            }
        )
        await send({"type": "http.response.body", "body": self.body})


class JSONResponse(Response):
    media_type = "application/json"
    encode_hook: Optional[Callable[[Any], Any]] = None

    def render(self, content: Any) -> bytes:
        return json.encode(content, enc_hook=self.encode_hook)


class MessagePackResponse(Response):
    media_type = "application/msgpack"
    encode_hook: Optional[Callable[[Any], Any]] = None

    def render(self, content: Any) -> bytes:
        return msgpack.encode(content, enc_hook=self.encode_hook)
