from collections.abc import Callable
from typing import TypeVar

from apispec_aiohttp.typedefs import HandlerType, IDataclass, SchemaType
from apispec_aiohttp.utils import get_or_set_apispec, get_or_set_schemas, resolve_schema_instance

T = TypeVar("T", bound=HandlerType)
TDataclass = TypeVar("TDataclass", bound=IDataclass)


def response_schema(
    schema: SchemaType | type[TDataclass],
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
            return web.json_response({"msg": "done", "data": {}})

    :param str description: response description
    :param bool required:
    :param schema: :class:`Schema <marshmallow.Schema>` class or instance
    :param int code: HTTP response code
    """
    schema_instance = resolve_schema_instance(schema)

    def wrapper(func: T) -> T:
        func_apispec = get_or_set_apispec(func)
        get_or_set_schemas(func)  # just to make sure schemas are initialized

        func_apispec["responses"][str(code)] = {
            "schema": schema_instance,
            "required": required,
            "description": description or "",
        }
        return func

    return wrapper
