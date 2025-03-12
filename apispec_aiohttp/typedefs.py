"""Type definitions for apispec-aiohttp."""

from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from aiohttp import web

HandlerType = Callable[..., Awaitable[web.StreamResponse]]


class IHandler(Protocol):
    """Protocol for API handler functions decorated with apispec decorators.

    These handlers have special attributes added to them by the decorators:
    - __apispec__: Contains OpenAPI documentation metadata
    - __schemas__: Contains request/response schema information
    """

    __apispec__: dict[str, Any]
    __schemas__: list[dict[str, Any]]

    def __call__(self, request: web.Request) -> Awaitable[web.StreamResponse]: ...
