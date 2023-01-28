from .app import Allin
from .context import _app_ctx, _request_ctx
from .local import LocalProxy
from .request import Request

current_app: Allin = LocalProxy(lambda: _app_ctx.get(None))
request: Request = LocalProxy(lambda: _request_ctx.get(None))
