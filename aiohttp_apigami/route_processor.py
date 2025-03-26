from collections.abc import Iterator

from aiohttp import web
from aiohttp.hdrs import METH_ALL
from apispec import APISpec

from .constants import API_SPEC_ATTR
from .data import RouteData
from .typedefs import HandlerType
from .utils import get_path, is_class_based_view


class RouteProcessor:
    """Processes aiohttp routes to extract OpenAPI data."""

    __slots__ = ("_prefix", "_spec")

    def __init__(self, spec: APISpec, prefix: str = ""):
        self._spec = spec
        self._prefix = prefix

    @staticmethod
    def _get_implemented_methods(class_based_view: HandlerType) -> Iterator[tuple[str, HandlerType]]:
        for m in METH_ALL:
            method_name = m.lower()
            if hasattr(class_based_view, method_name):
                yield method_name, getattr(class_based_view, method_name)

    @staticmethod
    def _has_spec(handler: HandlerType) -> bool:
        return hasattr(handler, API_SPEC_ATTR)

    def _iter_routes(self, app: web.Application) -> Iterator[RouteData]:
        for route in app.router.routes():
            path = get_path(route)
            if path is None:
                # Skip routes with no path
                continue

            path = self._prefix + path

            # Class based views have multiple methods
            if is_class_based_view(route.handler):
                for method_name, method_func in self._get_implemented_methods(route.handler):
                    if not self._has_spec(method_func):
                        # Ignore methods without spec data
                        continue

                    yield RouteData(method=method_name, path=path, handler=method_func)

            # Function based views have a single method
            else:
                method = route.method.lower()
                handler = route.handler

                if not self._has_spec(handler):
                    # Ignore methods without spec data
                    continue

                yield RouteData(method=method, path=path, handler=handler)

    def register_routes(self, app: web.Application) -> None:
        """Register all routes from the application."""
        for route in self._iter_routes(app):
            self.register_route(route)

    def register_route(self, route: RouteData) -> None:
        """Register a single route. It will be processed by AiohttpPlugin."""
        self._spec.path(path=route.path, method=route.method, handler=route.handler)
