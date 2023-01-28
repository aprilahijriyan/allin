import asyncio
from enum import IntEnum
from functools import partialmethod
from typing import Any, Callable, Optional

from autoroutes import Routes
from typing_extensions import TypeAlias

from .errors import EndpointError


class MatchingCode(IntEnum):
    NOT_FOUND = 0
    FOUND = 1
    UNSUPPORTED_METHODS = 2


MATCHED_ROUTE_TYPE: TypeAlias = tuple[
    Optional[dict[str, Any]], Optional[dict[str, Any]]
]


class Endpoint:
    """
    A class for defining an endpoint.
    """

    def __init__(self, path: str, func: Callable, methods: list[str]) -> None:
        self.path = path
        self.func = func
        self.methods = methods


class Router:
    """
    A router to create/find an endpoint.
    """

    def __init__(self, *, prefix: Optional[str] = None) -> None:
        """Create a router instance.

        Args:
            prefix: URL Prefix. For sub-routers, url prefix is required. Defaults to None.
        """
        if prefix is not None:
            assert prefix.startswith(
                "/"
            ), f"URL prefix {prefix!r} must start with '/'"  # noqa: S101
            assert not prefix.endswith(
                "/"
            ), f"URL prefix {prefix!r} should not end with '/'"  # noqa: S101
        self.prefix = prefix or ""
        self.routes = Routes()
        self.sub_routers: dict[str, "Router"] = {}

    def add_endpoint(self, path: str, func: Callable, *, methods: list[str]):
        """Adding an endpoint to the router.

        Args:
            path: Route path endpoint
            func: Endpoint function
            methods: HTTP Methods

        Raises:
            EndpointError: if endpoint already exists.
        """
        assert path.startswith("/"), "Path prefix must start with '/'"  # noqa: S101
        assert asyncio.iscoroutinefunction(
            func
        ), "The endpoint handler must be a coroutine function"  # noqa: S101
        assert isinstance(
            methods, list
        ), "'methods' param should be of type 'list'"  # noqa: S101
        path_endpoint = self.prefix + path
        methods = list({m.upper() for m in methods})
        matching_code, endpoint, _ = self.find(path_endpoint)
        if matching_code == MatchingCode.FOUND:
            changed = False
            for method in methods:
                if method not in endpoint.methods:
                    endpoint.methods.append(method)
                    changed = True
            if not changed:
                raise EndpointError(f"Endpoint with path {path!r} already exists")
        else:
            ep = Endpoint(path_endpoint, func, methods)
            self.routes.add(path_endpoint, endpoint=ep)

    def route(self, path: str, *, methods: list[str] = ["get", "head"]):  # noqa: B006
        """
        Add an endpoint with a decorator style
        """

        def inner(func: Callable):
            self.add_endpoint(path, func, methods=methods)
            return func

        return inner

    # Another shortcut for adding an endpoint with a decorator style
    get = partialmethod(route, methods=["get"])
    head = partialmethod(route, methods=["head"])
    post = partialmethod(route, methods=["post"])
    put = partialmethod(route, methods=["put"])
    delete = partialmethod(route, methods=["delete"])
    patch = partialmethod(route, methods=["patch"])
    options = partialmethod(route, methods=["options"])

    def find(
        self, path: str, method: Optional[str] = None
    ) -> tuple[MatchingCode, Endpoint, dict[str, Any]]:
        """Look up the endpoint based on the path on the router.

        Args:
            path: Route path endpoint
            method: HTTP Methods. Defaults to None.
        """
        path_parts = path.split("/")
        current_path = None
        router = None
        while len(path_parts) > 0:
            current_path = "/".join(path_parts)
            router = self.sub_routers.get(current_path)
            if router:
                break
            else:
                path_parts.pop(-1)

        if router:
            path = path.replace(current_path, router.prefix)
        else:
            router = self

        matched_route: MATCHED_ROUTE_TYPE = router.routes.match(path)
        handler_params, path_params = matched_route
        if handler_params is None and path_params is None:
            return (MatchingCode.NOT_FOUND, None, None)

        endpoint: Endpoint = handler_params["endpoint"]
        if method is not None and method.upper() not in endpoint.methods:
            return (MatchingCode.UNSUPPORTED_METHODS, None, None)

        return (MatchingCode.FOUND, endpoint, path_params)

    def include_router(self, router: "Router"):
        """Include a sub-router to this router.

        Args:
            router: Router instance

        Raises:
            EndpointError: if router already exists.
        """
        assert router.prefix, "URL prefix required for sub-router"  # noqa: S101
        router_url_prefix = self.prefix + router.prefix
        if router_url_prefix in self.sub_routers:
            raise EndpointError(f"Router with prefix {router.prefix!r} already exists")

        self.sub_routers[router_url_prefix] = router
        for router_prefix, sub_router in router.sub_routers.items():
            inherited_prefix = self.prefix + router_prefix
            if inherited_prefix in self.sub_routers:
                raise EndpointError(
                    f"Router with prefix {router_prefix!r} already exists"
                )
            self.sub_routers[inherited_prefix] = sub_router
