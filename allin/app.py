import asyncio
import traceback
from functools import partialmethod
from typing import Awaitable, Callable, Literal, Optional, TypeVar, Union

from asgi_typing import ASGIReceiveCallable, ASGISendCallable, HTTPScope, Scope
from typing_extensions import Concatenate, ParamSpec, TypeAlias

from .context import app_context, request_context
from .errors import AllinError, HTTPError, LostConnection
from .handlers import DEFAULT_ERROR_HANDLERS
from .parser import parse_headers
from .request import Request
from .response import Response
from .routing import MatchingCode, Router
from .status import status_codes
from .stream import BodyStream

P = ParamSpec("P")
T = TypeVar("T")
R = TypeVar("R")

EVENT_HANDLER_FUNC_TYPE: TypeAlias = Callable[[], Awaitable[R]]
ENDPOINT_HANDLER_TYPE: TypeAlias = Callable[Concatenate[Request, P], Awaitable[R]]
ERROR_HANDLER_TYPE: TypeAlias = Callable[
    [Exception, Optional[Request]], Awaitable[Response]
]


class Allin:
    """
    Allin application.
    """

    ROUTER_CLASS = Router

    def __init__(self) -> None:
        self.startup_handlers: list[EVENT_HANDLER_FUNC_TYPE] = []
        self.shutdown_handlers: list[EVENT_HANDLER_FUNC_TYPE] = []
        self.router = self.ROUTER_CLASS()
        self.error_handlers: dict[
            Union[status_codes, type[Exception]], ERROR_HANDLER_TYPE
        ] = DEFAULT_ERROR_HANDLERS

    def add_event_handler(
        self, event: Literal["startup", "shutdown"], handler: EVENT_HANDLER_FUNC_TYPE
    ) -> None:
        if not asyncio.iscoroutinefunction(handler):
            raise TypeError(f"The event handler {handler!r} must be a coroutine")

        if event == "startup":
            self.startup_handlers.append(handler)
        elif event == "shutdown":
            self.shutdown_handlers.append(handler)
        else:
            raise TypeError(f"Unknown event type: {event}")

    def on_startup(self, func: EVENT_HANDLER_FUNC_TYPE) -> EVENT_HANDLER_FUNC_TYPE:
        """
        A helper to add ASGI Lifespan 'startup' event handling functionality by using the 'decorator' style.

        Args:
            func: Handling function.
        """
        self.add_event_handler("startup", func)
        return func

    def on_shutdown(self, func: EVENT_HANDLER_FUNC_TYPE) -> EVENT_HANDLER_FUNC_TYPE:
        """A helper to add ASGI Lifespan 'shutdown' event handling functionality by using the 'decorator' style.

        Args:
            func: Handling function.
        """
        self.add_event_handler("shutdown", func)
        return func

    async def _handle_lifespan(
        self, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        """
        Handle ASGI Lifespan (`startup` and `shutdown`) events.
        See: https://asgi.readthedocs.io/en/latest/specs/lifespan.html#lifespan-protocol
        """
        while True:
            should_exit = False
            message = await receive()
            event = message["type"]
            if event == "lifespan.startup":
                handlers = self.startup_handlers
            elif event == "lifespan.shutdown":
                handlers = self.shutdown_handlers
                should_exit = True
            else:
                raise ValueError(f"Unknown lifespan event: {event}")

            try:
                for func in handlers:
                    await func()
            except Exception:
                await send({"type": f"{event}.failed"})
                traceback.print_exc()
                raise
            else:
                await send({"type": f"{event}.complete"})

            if should_exit:
                break

    # HTTP Methods decorators
    def route(self, path: str, *, methods: list[str] = ["get", "head"]):  # noqa: B006
        """A helper for adding routes using the 'decorator' style.

        Args:
            path: End point route. (e.g. `/some/path`)

        Keyword Arguments:
            methods: HTTP methods (default: `["get", "head"]`)
        """
        return self.router.route(path, methods=methods)

    get = partialmethod(route, methods=["get"])
    head = partialmethod(route, methods=["head"])
    post = partialmethod(route, methods=["post"])
    put = partialmethod(route, methods=["put"])
    delete = partialmethod(route, methods=["delete"])
    patch = partialmethod(route, methods=["patch"])
    options = partialmethod(route, methods=["options"])

    def include_router(self, router: Router):
        """Adding another router to the main router.

        Args:
            router: Router instance
        """
        self.router.include_router(router)

    def add_error_handler(
        self,
        code_or_exception: Union[status_codes, type[Exception]],
        func: ERROR_HANDLER_TYPE,
        force: bool = False,
    ):
        handler = self._find_error_handler(code_or_exception)
        if handler and not force:
            raise AllinError(f"Error handler for {code_or_exception!r} already exists")

        assert not isinstance(code_or_exception, int) and isinstance(
            code_or_exception, type
        ), "it takes a class for the 'code_or_exception' parameter"  # noqa: S101
        self.error_handlers[code_or_exception] = func

    def _find_error_handler(
        self, code_or_exception: Union[status_codes, type[Exception]]
    ) -> Optional[ERROR_HANDLER_TYPE]:
        """Function to look for handling functions based on 'HTTP status code' or exceptions.

        Args:
            code_or_exception: HTTP status code or exceptions
        """
        handler = None
        if isinstance(code_or_exception, int):
            handler = self.error_handlers.get(code_or_exception)
            return handler

        if not isinstance(code_or_exception, type):
            code_or_exception = type(code_or_exception)

        for ce, func in self.error_handlers.items():
            klass = code_or_exception.mro()[0]
            if ce == klass:
                handler = func
                break
        return handler

    async def _handle_http(
        self, scope: HTTPScope, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        """
        Handle HTTP requests.
        See: https://asgi.readthedocs.io/en/latest/specs/www.html#http
        """

        request = None
        try:
            message = await receive()
            event_type = message["type"]
            # Getting HTTP requests
            if event_type == "http.request":
                path = scope["path"]
                method = scope["method"]
                # Search for matching endpoints in Router.
                matching_code, endpoint, path_params = self.router.find(path, method)
                if matching_code == MatchingCode.FOUND:
                    headers = parse_headers(scope["headers"])
                    body = message["body"]
                    more_body = message["more_body"]
                    content_length = (
                        len(body) if not more_body else headers.content_length
                    )
                    stream = BodyStream(
                        receive=receive,
                        initial_buffer=body,
                        content_length=content_length,
                    )
                    request = Request(stream, scope, headers=headers)
                    with request_context(request):
                        response = await endpoint(**path_params)
                        if isinstance(response, Response):
                            await response(send=send)
                        else:
                            raise AllinError(
                                f"Function {endpoint.func} doesn't return a response object"
                            )
                elif matching_code == MatchingCode.NOT_FOUND:
                    raise HTTPError(status_codes.NOT_FOUND)
                elif matching_code == MatchingCode.UNSUPPORTED_METHODS:
                    raise HTTPError(status_codes.METHOD_NOT_ALLOWED)

        except LostConnection:
            # Just ignore it, if client connection is lost.
            pass

        except Exception as e:
            identifier = type(e)
            show_traceback = False
            handler = self._find_error_handler(identifier)
            if not handler:
                # If the handling function is not found for a particular exception.
                # Use the built in function to handle it and display the error traceback.
                handler = self._find_error_handler(Exception)
                show_traceback = True

            response = await handler(e, request)
            await response(send=send)
            if show_traceback:
                traceback.print_exc()

    async def __call__(
        self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        """
        Main entry point of a typical ASGI application.
        """
        event_type = scope["type"]
        assert event_type in (
            "http",
            "websocket",
            "lifespan",
        ), f"Unknown event {event_type!r}"
        with app_context(self):
            if event_type == "lifespan":
                await self._handle_lifespan(receive, send)

            async def _receive():
                # wrap original ASGI 'receive' function, to prevent if the client to server connection is lost.
                # This function will raise a LostConnection exception that will be handled by self._handle_http.
                message = await receive()
                if message["type"] == "http.disconnect":
                    raise LostConnection()
                return message

            if event_type == "http":
                await self._handle_http(scope, _receive, send)

            # todo: websocket support
