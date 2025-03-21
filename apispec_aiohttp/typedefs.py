"""Type definitions for apispec-aiohttp."""

from collections.abc import Awaitable, Callable

import marshmallow as m
from aiohttp import web

HandlerType = Callable[..., Awaitable[web.StreamResponse]]
SchemaType = type[m.Schema] | m.Schema
SchemaNameResolver = Callable[[type[m.Schema]], str]
