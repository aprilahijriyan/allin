from enum import IntEnum
from functools import cached_property
from typing import Any, Optional, Union

from multipart.multipart import MultipartParser, parse_options_header

from .errors import HTTPError
from .params import BodyPart, UploadFile
from .status import status_codes
from .stream import BodyStream


class HttpHeaders(dict):
    def __init__(self, raw: dict[str, str]) -> None:
        super().__init__(raw)

    def __setitem__(self, __key: str, __value: str) -> None:
        raise NotImplementedError("You cannot modify the HTTP request header")

    def __getitem__(self, k: str):
        k = k.lower()
        return super().__getitem__(k)

    def get(self, k: str, default: Any = None) -> str:
        return super().get(k.lower(), default)

    @cached_property
    def user_agent(self) -> Optional[str]:
        return self.get("user-agent")

    @cached_property
    def host(self) -> Optional[str]:
        return self.get("host")

    @cached_property
    def connection(self) -> Optional[str]:
        return self.get("connection")

    @cached_property
    def accept(self) -> Optional[str]:
        return self.get("accept")

    @cached_property
    def referer(self) -> Optional[str]:
        return self.get("referer")

    @cached_property
    def accept_encoding(self) -> Optional[str]:
        return self.get("accept-encoding")

    @cached_property
    def accept_language(self) -> Optional[str]:
        return self.get("accept-language")

    @cached_property
    def content_type(self) -> Optional[str]:
        return self.get("content-type")

    @cached_property
    def content_length(self) -> Optional[int]:
        return int(self.get("content-length", 0))

    def __str__(self) -> str:
        return f"<{type(self).__name__}: {dict(self)}>"


def parse_headers(headers: list[tuple[bytes, bytes]]) -> HttpHeaders:
    data = {k.lower().decode("latin-1"): v.decode("latin-1") for k, v in headers}
    return HttpHeaders(data)


class MultiPartMessage(IntEnum):
    """
    This is part of the `starlette`.
    See: https://github.com/encode/starlette/blob/master/starlette/formparsers.py#L23
    """

    PART_BEGIN = 1
    PART_DATA = 2
    PART_END = 3
    HEADER_FIELD = 4
    HEADER_VALUE = 5
    HEADER_END = 6
    HEADERS_FINISHED = 7
    END = 8


class FormDataParser:
    """
    This is part of the `starlette`.
    See: https://github.com/encode/starlette/blob/master/starlette/formparsers.py#L118

    There are only a few changes to suit the `Allin` framework.
    """

    def __init__(self, content_type: str) -> None:
        _, params = parse_options_header(content_type)
        boundary = params.get(b"boundary")
        callbacks = {
            "on_part_begin": self.on_part_begin,
            "on_part_data": self.on_part_data,
            "on_part_end": self.on_part_end,
            "on_header_field": self.on_header_field,
            "on_header_value": self.on_header_value,
            "on_header_end": self.on_header_end,
            "on_headers_finished": self.on_headers_finished,
            "on_end": self.on_end,
        }
        self.parser = MultipartParser(boundary, callbacks=callbacks)
        self._body_parts: list[tuple[MultiPartMessage, bytes]] = []

    def on_part_begin(self):
        self._body_parts.append((MultiPartMessage.PART_BEGIN, b""))

    def on_part_data(self, data: bytes, start: int, end: int):
        value = data[start:end]
        self._body_parts.append((MultiPartMessage.PART_DATA, value))

    def on_part_end(self):
        self._body_parts.append((MultiPartMessage.PART_END, b""))

    def on_header_field(self, data: bytes, start: int, end: int):
        header_name = data[start:end]
        self._body_parts.append((MultiPartMessage.HEADER_FIELD, header_name))

    def on_header_value(self, data: bytes, start: int, end: int):
        header_value = data[start:end]
        self._body_parts.append((MultiPartMessage.HEADER_VALUE, header_value))

    def on_header_end(self):
        self._body_parts.append((MultiPartMessage.HEADER_END, b""))

    def on_headers_finished(self):
        self._body_parts.append((MultiPartMessage.HEADERS_FINISHED, b""))

    def on_end(self):
        self._body_parts.append((MultiPartMessage.END, b""))

    async def parse(self, stream: BodyStream):  # noqa: C901
        header_field = b""
        header_value = b""
        content_disposition = None
        content_type = b""
        field_name = ""
        data = b""
        file: Optional[UploadFile] = None
        items: list[tuple[str, Union[BodyPart, UploadFile]]] = []
        item_headers: list[tuple[str, str]] = []
        charset = "latin-1"
        async for chunk in stream:
            # print("Chunk:", len(chunk))
            self.parser.write(chunk)
            parts = list(self._body_parts)
            self._body_parts.clear()
            for message_type, message_bytes in parts:
                if message_type == MultiPartMessage.PART_BEGIN:
                    content_disposition = None
                    content_type = b""
                    data = b""
                    item_headers = []
                elif message_type == MultiPartMessage.HEADER_FIELD:
                    header_field += message_bytes
                elif message_type == MultiPartMessage.HEADER_VALUE:
                    header_value += message_bytes
                elif message_type == MultiPartMessage.HEADER_END:
                    field = header_field.lower()
                    if field == b"content-disposition":
                        content_disposition = header_value
                    elif field == b"content-type":
                        content_type = header_value
                    item_headers.append(
                        (field.decode(charset), header_value.decode(charset))
                    )
                    header_field = b""
                    header_value = b""
                elif message_type == MultiPartMessage.HEADERS_FINISHED:
                    disposition, options = parse_options_header(content_disposition)
                    try:
                        field_name = options[b"name"].decode(charset)
                    except KeyError as e:
                        raise HTTPError(
                            status_codes.UNSUPPORTED_MEDIA_TYPE,
                            detail="Invalid multipart/form-data request. Missing 'name' field.",
                        ) from e

                    if b"filename" in options:
                        filename = options[b"filename"].decode(charset)
                        file = await UploadFile.create(
                            filename=filename,
                            content_type=content_type.decode(charset),
                            headers=dict(item_headers),
                        )
                    else:
                        file = None
                elif message_type == MultiPartMessage.PART_DATA:
                    if file is None:
                        data += message_bytes
                    else:
                        await file.write(message_bytes)
                elif message_type == MultiPartMessage.PART_END:
                    if file is None:
                        part = BodyPart(
                            data.decode(charset),
                            content_type.decode(charset),
                            headers=dict(item_headers),
                        )
                        items.append((field_name, part))
                    else:
                        await file.seek(0)
                        items.append((field_name, file))
        self.parser.finalize()
        return items
