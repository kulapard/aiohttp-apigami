"""Type definitions for apispec-aiohttp."""

import dataclasses
from collections.abc import Awaitable, Callable
from typing import Any, ClassVar, Protocol

import marshmallow as m
from aiohttp import web

HandlerType = Callable[..., Awaitable[web.StreamResponse]]
SchemaType = type[m.Schema] | m.Schema
SchemaNameResolver = Callable[[type[m.Schema]], str]


class IDataclass(Protocol):
    __dataclass_fields__: ClassVar[dict[str, dataclasses.Field[Any]]]
