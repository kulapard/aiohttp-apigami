from collections.abc import Iterator
from dataclasses import dataclass

from aiohttp import web
from aiohttp.hdrs import METH_ALL

from .constants import API_SPEC_ATTR
from .processors import create_processor
from .spec import SpecManager
from .typedefs import HandlerType
from .utils import get_path, is_class_based_view


@dataclass(frozen=True, slots=True, kw_only=True)
class RouteData:
    method: str
    path: str
    handler: HandlerType


class RouteProcessor:
    """Processes aiohttp routes to extract OpenAPI data."""

    __slots__ = ("_prefix", "_processor", "_spec_manager")

    def __init__(self, spec_manager: SpecManager, prefix: str = ""):
        self._spec_manager = spec_manager
        self._prefix = prefix
        self._processor = create_processor(spec_manager)

    @staticmethod
    def _get_implemented_methods(class_based_view: HandlerType) -> Iterator[tuple[str, HandlerType]]:
        for m in METH_ALL:
            method_name = m.lower()
            if hasattr(class_based_view, method_name):
                yield method_name, getattr(class_based_view, method_name)

    def _iter_routes(self, app: web.Application) -> Iterator[RouteData]:
        for route in app.router.routes():
            # Class based views have multiple methods
            if is_class_based_view(route.handler):
                for method_name, method_func in self._get_implemented_methods(route.handler):
                    path = get_path(route)
                    if path is not None:
                        yield RouteData(method=method_name, path=path, handler=method_func)

            # Function based views have a single method
            else:
                path = get_path(route)
                if path is not None:
                    method = route.method.lower()
                    handler = route.handler
                    yield RouteData(method=method, path=path, handler=handler)

    def register_routes(self, app: web.Application) -> None:
        """Register all routes from the application."""
        for route in self._iter_routes(app):
            self.register_route(route)

    def register_route(self, route: RouteData) -> None:
        """Register a single route."""
        if not hasattr(route.handler, API_SPEC_ATTR):
            # No OpenAPI data found in the handler
            return None

        handler_apispec = getattr(route.handler, API_SPEC_ATTR)
        full_path = self._prefix + route.path
        handler_apispec = self._processor.get_path_operations(
            path=full_path, method=route.method, handler_apispec=handler_apispec
        )
        if handler_apispec is None:
            # No OpenAPI data found in the handler
            return None

        self._spec_manager.add_path(path=full_path, method=route.method, handler_apispec=handler_apispec)
