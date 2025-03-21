from inspect import isclass
from string import Formatter

from aiohttp import web
from aiohttp.abc import AbstractView
from aiohttp.typedefs import Handler


def get_path(route: web.AbstractRoute) -> str | None:
    """Get path string from a route."""
    if route.resource is None:
        return None
    return route.resource.canonical


def get_path_keys(path: str) -> list[str]:
    """Get path keys from a path string."""
    return [i[1] for i in Formatter().parse(path) if i[1]]


def is_class_based_view(handler: Handler | type[AbstractView]) -> bool:
    """Check if the handler is a class-based view."""
    if not isclass(handler):
        return False

    return issubclass(handler, web.View)
