from typing import Any, cast

from aiohttp import web
from aiohttp.typedefs import Handler

from .aiohttp import APISPEC_PARSER, APISPEC_VALIDATED_DATA_NAME, HandlerSchema
from .utils import issubclass_py37fix


def _get_handler_schemas(request: web.Request) -> list[HandlerSchema] | None:
    """
    Get schemas from the request handler
    """
    handler = request.match_info.handler

    if hasattr(handler, "__schemas__"):
        return cast(list[HandlerSchema], handler.__schemas__)

    if issubclass_py37fix(handler, web.View):
        sub_handler = getattr(handler, request.method.lower(), None)
        if sub_handler and hasattr(sub_handler, "__schemas__"):
            return cast(list[HandlerSchema], sub_handler.__schemas__)

    return None


async def _get_validated_data(request: web.Request, schema: HandlerSchema) -> Any | None:
    """
    Parse and validate request data using the schema
    """
    return await request.app[APISPEC_PARSER].parse(
        schema.schema,
        request,
        location=schema.location,
        unknown=None,  # Pass None to use the schema`s setting instead.
    )


@web.middleware
async def validation_middleware(request: web.Request, handler: Handler) -> web.StreamResponse:
    """
    Validation middleware for aiohttp web app

    Usage:

    .. code-block:: python

        app.middlewares.append(validation_middleware)


    """
    schemas = _get_handler_schemas(request)
    if schemas is None:
        # Skip validation if no schemas are found
        return await handler(request)

    result = []
    for sch in schemas:
        # Parse and validate request data using the schema
        data = await _get_validated_data(request, sch)

        # If put_into is specified, store the validated data in a specific key
        if sch.put_into:
            request[sch.put_into] = data

        # Otherwise, store the validated data in the default key
        elif data:
            try:
                # TODO: refactor to avoid mixing data from different schemas
                if isinstance(data, list):
                    result.extend(data)
                else:
                    result = data
            except (ValueError, TypeError):
                result = data
                break

    # Store validated data in request object
    request[request.app[APISPEC_VALIDATED_DATA_NAME]] = result
    return await handler(request)
