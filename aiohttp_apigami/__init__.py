# mypy: disable-error-code="attr-defined"
from importlib import metadata

from .core import AiohttpApiSpec, OpenApiVersion, setup_aiohttp_apispec
from .decorators import (
    cookies_schema,
    docs,
    form_schema,
    headers_schema,
    json_schema,
    match_info_schema,
    querystring_schema,
    request_schema,
    response_schema,
)
from .middlewares import validation_middleware

__all__ = [
    "AiohttpApiSpec",
    "OpenApiVersion",
    "__version__",
    "cookies_schema",
    "docs",
    "form_schema",
    "headers_schema",
    "json_schema",
    "match_info_schema",
    "querystring_schema",
    "request_schema",
    "response_schema",
    "setup_aiohttp_apispec",
    "validation_middleware",
]

__version__ = metadata.version(__package__)
