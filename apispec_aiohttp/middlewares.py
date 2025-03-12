from typing import Any, cast

from aiohttp import web
from aiohttp.typedefs import Handler

from .aiohttp import APISPEC_PARSER, APISPEC_VALIDATED_DATA_NAME, HandlerSchema
from .utils import issubclass_py37fix

_Schema = dict[str, str]


def _get_schemas(handler: Handler) -> list[HandlerSchema] | None:
    """
    Get schemas from handler
    """
    if hasattr(handler, "__schemas__"):
        return cast(list[HandlerSchema], handler.__schemas__)

    if issubclass_py37fix(handler, web.View):
        sub_handler = getattr(handler, "get", None)
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
    orig_handler = request.match_info.handler
    schemas = _get_schemas(orig_handler)
    if schemas is None:
        # Skip validation if no schemas are found
        return await handler(request)

    result = []
    for schema_config in schemas:
        # Parse and validate request data using the schema
        data = await _get_validated_data(request, schema_config)

        # If put_into is specified, store the validated data in a specific key
        if schema_config.put_into:
            request[schema_config.put_into] = data

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
