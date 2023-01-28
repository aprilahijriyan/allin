from functools import cached_property
from typing import Any, Callable, Optional, Union

from asgi_typing import HTTPScope
from biscuits import parse as parse_cookie
from fast_query_parsers import parse_query_string, parse_url_encoded_dict
from msgspec import Struct, json, msgpack

from .errors import MediaTypeError
from .params import BodyPart, UploadFile
from .parser import FormDataParser, HttpHeaders
from .stream import BodyStream


class Request:
    """
    An object that represents an HTTP request.
    """

    media_types = {
        "json": ["application/json"],
        "msgpack": ["application/msgpack"],
        "form-urlencoded": ["application/x-www-form-urlencoded"],
        "form-data": ["multipart/form-data"],
    }

    def __init__(
        self, stream: BodyStream, scope: HTTPScope, *, headers: HttpHeaders = None
    ) -> None:
        self.stream = stream
        self.headers = headers
        self.scope = scope
        self._query = {}
        self._forms: dict[str, Optional[Union[str, UploadFile]]] = {}
        self._json = {}
        self._msgpack = {}

    async def body(self) -> bytes:
        """
        Get all request bodies in one fetch.
        """
        return await self.stream.read()

    @property
    def client(self):
        return self.scope["client"]

    @property
    def server(self):
        return self.scope["server"]

    @property
    def http_version(self):
        return self.scope["http_version"]

    @property
    def method(self):
        return self.scope["method"]

    @property
    def path(self):
        return self.scope["path"]

    @property
    def root_path(self):
        return self.scope["root_path"]

    @property
    def scheme(self):
        return self.scope["scheme"]

    @property
    def content_length(self) -> int:
        return self.headers.content_length

    @property
    def content_type(self) -> str:
        return self.headers.content_type

    @cached_property
    def cookies(self) -> dict[str, Any]:
        return parse_cookie(self.headers.get("cookie", ""))

    def _check_media_type(
        self, media_type: str, *, deep_check: bool = False, silent: bool = False
    ):
        """
        Validate content type on HTTP request.
        """
        media_types = self.media_types.get(media_type)
        content_type = self.headers.content_type
        has_error = False
        if media_types and content_type:
            if deep_check:
                has_error = not any(
                    filter(lambda x: content_type.startswith(x.strip()), media_types)
                )
            else:
                has_error = self.content_type not in media_types
            if has_error and not silent:
                raise MediaTypeError(
                    f"Client asks for {content_type} but you expect {media_type!r}"
                )
        return not has_error

    def query(self, separator: str = "&") -> dict[str, Any]:
        """
        Parse the query string to a dictionary.
        """
        if self._query:
            return self._query
        qs: bytes = self.scope["query_string"]
        query = {}
        for k, v in parse_query_string(qs, separator):
            kv = query.get(k)
            if k in query:
                if not isinstance(kv, list):
                    v = [kv, v]
                else:
                    kv.append(v)
                    v = kv
            query[k] = v
        self._query = query
        return self._query

    async def json(
        self,
        schema: Struct = None,
        *,
        decode_hook: Optional[Callable[[type, Any], Any]] = None,
    ) -> Union[dict, list]:
        """
        Parse the JSON request body

        Args:
            schema: `msgspec.Struct` object to validate request body.
                    If given, it will run validation. Defaults to None.
            decode_hook: See https://jcristharif.com/msgspec/api.html#msgspec.json.decode.
                        Defaults to None.
        """
        if self._json:
            return self._json

        if self._check_media_type("json", silent=True):
            body = await self.body()
            data = json.decode(body, type=schema, dec_hook=decode_hook)
            self._json = data

        return self._json

    async def msgpack(
        self,
        schema: Struct = None,
        *,
        decode_hook: Optional[Callable[[type, Any], Any]] = None,
    ) -> Union[dict, list]:
        """
        Parse the msgpack request body

        Args:
            schema: `msgspec.Struct` object to validate request body.
                    If given, it will run validation. Defaults to None.
            decode_hook: See https://jcristharif.com/msgspec/api.html#msgspec.msgpack.decode. Defaults to None.
        """
        if self._msgpack:
            return self._msgpack

        if self._check_media_type("msgpack", silent=True):
            body = await self.body()
            data = msgpack.decode(body, type=schema, dec_hook=decode_hook)
            self._msgpack = data
        return self._msgpack

    async def forms(
        self,
        schema: Struct = None,
        *,
        encode_hook: Optional[Callable[[Any], Any]] = None,
        decode_hook: Optional[Callable[[type, Any], Any]] = None,
    ) -> Union[dict[str, Any], dict[str, Union[BodyPart, UploadFile]]]:
        """
        Parse the request body of the `application/x-www-form-urlencoded` or `multipart/form-data` content type.

        Args:
            schema: `msgspec.Struct` object to validate request body.
                    If given, it will run validation (Only for `application/x-www-form-urlencoded`). Defaults to None.
            encode_hook: See https://jcristharif.com/msgspec/api.html#msgspec.json.encode. Defaults to None.
            decode_hook: See https://jcristharif.com/msgspec/api.html#msgspec.json.decode. Defaults to None.

        Returns:
            Dict[str, Any]: if request body is `application/x-www-form-urlencoded`
            Dict[str, Union[BodyPart, UploadFile]]: if request body is `multipart/form-data`
        """
        if self._forms:
            return self._forms

        if self._check_media_type("form-urlencoded", silent=True):
            body = await self.body()
            data = parse_url_encoded_dict(body)
            if schema:
                json.decode(
                    json.encode(data, enc_hook=encode_hook),
                    type=schema,
                    dec_hook=decode_hook,
                )

            self._forms = data

        elif self._check_media_type("form-data", deep_check=True, silent=True):
            parser = FormDataParser(self.headers.content_type)
            forms = {}
            items = await parser.parse(self.stream)
            for field_name, field_value in items:
                if field_name in forms:
                    fv = forms.get(field_name)
                    if not isinstance(fv, list):
                        fv = [fv, field_value]
                    else:
                        fv.append(field_value)
                    field_value = fv
                forms[field_name] = field_value
            self._forms = forms

        return self._forms
