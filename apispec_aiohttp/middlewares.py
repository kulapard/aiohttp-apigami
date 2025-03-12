from aiohttp import web
from aiohttp.typedefs import Handler

from .aiohttp import APISPEC_PARSER, APISPEC_REQUEST_DATA_NAME
from .utils import issubclass_py37fix


@web.middleware
async def validation_middleware(request: web.Request, handler: Handler) -> web.StreamResponse:
    """
    Validation middleware for aiohttp web app

    Usage:

    .. code-block:: python

        app.middlewares.append(validation_middleware)


    """
    orig_handler = request.match_info.handler
    if not hasattr(orig_handler, "__schemas__"):
        if not issubclass_py37fix(orig_handler, web.View):
            return await handler(request)
        sub_handler = getattr(orig_handler, request.method.lower(), None)
        if sub_handler is None:
            return await handler(request)
        if not hasattr(sub_handler, "__schemas__"):
            return await handler(request)
        schemas = sub_handler.__schemas__
    else:
        schemas = orig_handler.__schemas__
    result = []
    for schema in schemas:
        data = await request.app[APISPEC_PARSER].parse(
            schema["schema"],
            request,
            location=schema["location"],
            unknown=None,  # Pass None to use the schema`s setting instead.
        )
        if schema["put_into"]:
            request[schema["put_into"]] = data
        elif data:
            try:
                if isinstance(data, list):
                    result.extend(data)
                else:
                    result = data
            except (ValueError, TypeError):
                result = data
                break
    request[request.app[APISPEC_REQUEST_DATA_NAME]] = result
    return await handler(request)
