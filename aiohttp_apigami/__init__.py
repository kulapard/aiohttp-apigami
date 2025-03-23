# mypy: disable-error-code="attr-defined"
from importlib import metadata

from .core import AiohttpApiSpec, OpenApiVersion, setup_apispec_aiohttp
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
from .processors import BaseOpenAPIProcessor, OpenAPIv2Processor, OpenAPIv3Processor, create_processor

__all__ = [
    "AiohttpApiSpec",
    "BaseOpenAPIProcessor",
    "OpenAPIv2Processor",
    "OpenAPIv3Processor",
    "OpenApiVersion",
    "__version__",
    "cookies_schema",
    "create_processor",
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
