from aiohttp import web
from aiohttp.hdrs import METH_ALL, METH_ANY

from .constants import API_SPEC_ATTR
from .processors import create_processor
from .spec import SpecManager
from .typedefs import HandlerType
from .utils import get_path, is_class_based_view


class RouteProcessor:
    """Processes aiohttp routes to extract OpenAPI data."""

    __slots__ = ("_prefix", "_processor", "_spec_manager")

    def __init__(self, spec_manager: SpecManager, prefix: str = ""):
        self._spec_manager = spec_manager
        self._prefix = prefix
        self._processor = create_processor(spec_manager)

    def register_routes(self, app: web.Application) -> None:
        """Register all routes from the application."""
        for route in app.router.routes():
            # Class based views have multiple methods
            # Register each method separately
            if is_class_based_view(route.handler) and route.method == METH_ANY:
                for attr in dir(route.handler):
                    if attr.upper() in METH_ALL:
                        method = attr
                        sub_handler = getattr(route.handler, attr)
                        self.register_route(route=route, method=method, handler=sub_handler)

            # Function based views have a single method
            else:
                method = route.method.lower()
                handler = route.handler
                self.register_route(route=route, method=method, handler=handler)

    def register_route(self, *, route: web.AbstractRoute, method: str, handler: HandlerType) -> None:
        """Register a single route."""
        if not hasattr(handler, API_SPEC_ATTR):
            return None

        url_path = get_path(route)
        if not url_path:
            return None

        handler_apispec = getattr(handler, API_SPEC_ATTR, {})
        full_path = self._prefix + url_path
        handler_apispec = self._processor.get_path_operations(
            path=full_path, method=method, handler_apispec=handler_apispec
        )
        if handler_apispec is not None:
            self._spec_manager.add_path(path=full_path, method=method, handler_apispec=handler_apispec)
