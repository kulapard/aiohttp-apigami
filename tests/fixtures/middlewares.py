from typing import Any, NoReturn

import marshmallow as m
import pytest
from aiohttp import web
from aiohttp.typedefs import Handler, Middleware

from aiohttp_apigami.typedefs import ErrorHandler
from tests.fixtures.schemas import MyException


@pytest.fixture
def error_handler() -> ErrorHandler:
    def my_error_handler(error: m.ValidationError, *_: Any, **__: Any) -> NoReturn:
        raise MyException({"errors": error.messages, "text": "Oops"})

    return my_error_handler


@pytest.fixture
def error_middleware() -> Middleware:
    @web.middleware
    async def intercept_error(request: web.Request, handler: Handler) -> web.StreamResponse:
        try:
            return await handler(request)
        except MyException as e:
            return web.json_response(e.message, status=400)

    return intercept_error
