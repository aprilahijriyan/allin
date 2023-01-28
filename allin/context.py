import typing
from contextlib import contextmanager
from contextvars import ContextVar

if typing.TYPE_CHECKING:
    from .app import Allin
    from .request import Request

_app_ctx = ContextVar("_app_ctx")
_request_ctx = ContextVar("_request_ctx")


@contextmanager
def app_context(app: "Allin") -> typing.Iterator[None]:
    token = _app_ctx.set(app)
    yield
    _app_ctx.reset(token)


@contextmanager
def request_context(request: "Request") -> typing.Iterator[None]:
    token = _request_ctx.set(request)
    yield
    _request_ctx.reset(token)
