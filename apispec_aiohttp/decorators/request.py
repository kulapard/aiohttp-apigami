import copy
from collections.abc import Callable
from functools import partial
from typing import Any, Literal, TypeVar

import marshmallow as ma

from apispec_aiohttp.aiohttp import HandlerSchema
from apispec_aiohttp.typedefs import HandlerType

# Locations supported by both openapi and webargs.aiohttpparser
ValidLocations = Literal[
    "cookies",
    "files",
    "form",
    "headers",
    "json",
    "match_info",
    "path",
    "query",
    "querystring",
]

VALID_SCHEMA_LOCATIONS = (
    "cookies",
    "files",
    "form",
    "headers",
    "json",
    "match_info",
    "path",
    "query",
    "querystring",
)

T = TypeVar("T", bound=HandlerType)


def request_schema(
    schema: ma.Schema | type[ma.Schema],
    location: ValidLocations = "json",
    put_into: str | None = None,
    example: dict[str, Any] | None = None,
    add_to_refs: bool = False,
    **kwargs: Any,
) -> Callable[[T], T]:
    """
    Add request info into the swagger spec and
    prepare injection keyword arguments from the specified
    webargs arguments into the decorated view function in
    request['data'] for validation_middleware validation middleware.

    Usage:

    .. code-block:: python

        from aiohttp import web
        from marshmallow import Schema, fields


        class RequestSchema(Schema):
            id = fields.Int()
            name = fields.Str(description='name')

        @request_schema(RequestSchema(strict=True))
        async def index(request):
            # apispec_aiohttp_middleware should be used for it
            data = request['data']
            return web.json_response({'name': data['name'],
                                      'id': data['id']})

    :param schema: :class:`Schema <marshmallow.Schema>` class or instance
    :param location: Default request locations to parse
    :param put_into: name of the key in Request object
                     where validated data will be placed.
                     If None (by default) default key will be used
    :param dict example: Adding example for current schema
    :param bool add_to_refs: Working only if example not None,
                             if True, add example for ref schema.
                             Otherwise add example to endpoint.
                             Default False
    """

    if location not in VALID_SCHEMA_LOCATIONS:
        raise ValueError(f"Invalid location argument: {location}")

    schema_instance: ma.Schema
    if callable(schema):
        schema_instance = schema()
    else:
        schema_instance = schema

    options = {"required": kwargs.pop("required", False)}

    def wrapper(func: T) -> T:
        if not hasattr(func, "__apispec__"):
            func.__apispec__ = {"schemas": [], "responses": {}, "parameters": []}  # type: ignore[attr-defined]
            func.__schemas__: list[HandlerSchema] = []  # type: ignore

        func_schemas: list[HandlerSchema] = func.__schemas__  # type: ignore

        _example = copy.copy(example) or {}
        if _example:
            _example["add_to_refs"] = add_to_refs

        func.__apispec__["schemas"].append(  # type: ignore
            {
                "schema": schema_instance,
                "location": location,
                "options": options,
                "example": _example,
            }
        )

        # TODO: raise error if same location is used multiple times (no only for json)
        if location == "json" and any(sch.location == "json" for sch in func_schemas):
            raise RuntimeError("Multiple json locations are not allowed")

        func_schemas.append(
            HandlerSchema(
                schema=schema_instance,
                location=location,
                put_into=put_into,
            )
        )

        return func

    return wrapper


# Decorators for specific request data validations (shortenings)
match_info_schema = partial(request_schema, location="match_info", put_into="match_info")
querystring_schema = partial(request_schema, location="querystring", put_into="querystring")
form_schema = partial(request_schema, location="form", put_into="form")
json_schema = partial(request_schema, location="json", put_into="json")
headers_schema = partial(request_schema, location="headers", put_into="headers")
cookies_schema = partial(request_schema, location="cookies", put_into="cookies")
