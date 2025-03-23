from dataclasses import is_dataclass
from inspect import isclass
from string import Formatter
from typing import Any, TypeVar

import marshmallow as m
from aiohttp import web
from aiohttp.abc import AbstractView
from aiohttp.typedefs import Handler

from .constants import API_SPEC_ATTR, SCHEMAS_ATTR
from .typedefs import IDataclass, SchemaType
from .validation import ValidationSchema

try:
    import marshmallow_recipe as mr

except ImportError:  # pragma: no cover
    mr = None  # type: ignore

T = TypeVar("T")
TDataclass = TypeVar("TDataclass", bound=IDataclass)


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


def get_or_set_apispec(func: T) -> dict[str, Any]:
    func_apispec: dict[str, Any]
    if hasattr(func, API_SPEC_ATTR):
        func_apispec = getattr(func, API_SPEC_ATTR)
    else:
        func_apispec = {"schemas": [], "responses": {}, "parameters": []}
        setattr(func, API_SPEC_ATTR, func_apispec)
    return func_apispec


def get_or_set_schemas(func: T) -> list[ValidationSchema]:
    func_schemas: list[ValidationSchema]
    if hasattr(func, SCHEMAS_ATTR):
        func_schemas = getattr(func, SCHEMAS_ATTR)
    else:
        func_schemas = []
        setattr(func, SCHEMAS_ATTR, func_schemas)
    return func_schemas


def resolve_schema_instance(schema: SchemaType | type[TDataclass]) -> m.Schema:
    if isinstance(schema, type) and issubclass(schema, m.Schema):
        return schema()
    if isinstance(schema, m.Schema):
        return schema
    if is_dataclass(schema):
        if mr is None:
            raise RuntimeError(
                "marshmallow-recipe is required for dataclass support. "
                "Install it with `pip install aiohttp-apigami[dataclass]`."
            )
        return mr.schema(schema)

    raise ValueError(f"Invalid schema type: {schema}")
