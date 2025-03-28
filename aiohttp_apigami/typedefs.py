"""Type definitions for aiohttp-apigami."""

import dataclasses
from collections.abc import Awaitable, Callable
from typing import Any, ClassVar, NoReturn, Protocol

import marshmallow as m
from aiohttp import web

HandlerType = Callable[..., Awaitable[web.StreamResponse]]
SchemaType = type[m.Schema] | m.Schema
SchemaNameResolver = Callable[[type[m.Schema]], str]


class IDataclass(Protocol):
    __dataclass_fields__: ClassVar[dict[str, dataclasses.Field[Any]]]


class ErrorHandler(Protocol):
    def __call__(
        self,
        error: m.ValidationError,
        req: web.Request,
        schema: m.Schema,
        *args: Any,
        error_status_code: int,
        error_headers: dict[str, str],
    ) -> NoReturn: ...
