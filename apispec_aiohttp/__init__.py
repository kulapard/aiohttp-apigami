# mypy: disable-error-code="attr-defined"
from importlib import metadata

from .aiohttp import AiohttpApiSpec, setup_apispec_aiohttp
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
from .typedefs import IHandler

__all__ = [
    "AiohttpApiSpec",
    "IHandler",
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
    "setup_apispec_aiohttp",
    "validation_middleware",
]

__version__ = metadata.version(__package__)
