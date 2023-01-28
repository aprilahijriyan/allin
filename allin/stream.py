from asgi_typing import ASGIReceiveCallable


class BodyStream:
    """
    The simple class retrieves a large request body from the ASGI server.
    """

    def __init__(
        self, receive: ASGIReceiveCallable, initial_buffer: bytes, content_length: int
    ) -> None:
        self._receive = receive
        self._buffer = initial_buffer
        self._bytes_remaining = content_length - len(initial_buffer)
        self._is_initial_buffer = True

    async def __aiter__(self):
        yield self._buffer
        while self._bytes_remaining > 0:
            message = await self._receive()
            self._is_initial_buffer = False
            chunk = message["body"]
            body_length = len(chunk)
            self._bytes_remaining -= body_length
            yield chunk

            more_body = message["more_body"]
            if not more_body:
                break
            if self._bytes_remaining <= 0:
                break
        yield b""

    async def read(self, size: int = None):
        if self._bytes_remaining <= 0:
            return self._buffer

        if size == 0:
            return b""

        body_length = len(self._buffer)
        if size is not None and size > 0 and body_length >= size:
            body = self._buffer[:size]
            self._buffer = self._buffer[size:]
            return body

        async for chunk in self:
            if not self._is_initial_buffer:
                self._buffer += chunk
            if size is not None and size > 0 and len(self._buffer) >= size:
                break

        if size is not None and size > 0:
            body = self._buffer[:size]
            self._buffer = self._buffer[size:]
        else:
            body = self._buffer
            self._buffer = b""

        return body
