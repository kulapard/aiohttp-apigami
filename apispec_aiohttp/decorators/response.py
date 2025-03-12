from collections.abc import Callable
from typing import TypeVar

import marshmallow as m

from apispec_aiohttp.typedefs import HandlerType

T = TypeVar("T", bound=HandlerType)


def response_schema(
    schema: type[m.Schema] | m.Schema,
    code: int = 200,
    required: bool = False,
    description: str | None = None,
) -> Callable[[T], T]:
    """
    Add response info into the swagger spec

    Usage:

    .. code-block:: python

        from aiohttp import web
        from marshmallow import Schema, fields


        class ResponseSchema(Schema):
            msg = fields.Str()
            data = fields.Dict()

        @response_schema(ResponseSchema(), 200)
        async def index(request):
            return web.json_response({'msg': 'done', 'data': {}})

    :param str description: response description
    :param bool required:
    :param schema: :class:`Schema <marshmallow.Schema>` class or instance
    :param int code: HTTP response code
    """
    if callable(schema):
        schema = schema()

    def wrapper(func: T) -> T:
        if not hasattr(func, "__apispec__"):
            func.__apispec__ = {"schemas": [], "responses": {}, "parameters": []}  # type: ignore[attr-defined]
            func.__schemas__ = []  # type: ignore[attr-defined]
        func.__apispec__["responses"][f"{code}"] = {  # type: ignore[attr-defined]
            "schema": schema,
            "required": required,
            "description": description or "",
        }
        return func

    return wrapper
