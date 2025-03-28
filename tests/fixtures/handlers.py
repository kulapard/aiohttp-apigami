from dataclasses import dataclass
from typing import Any

import pytest
from aiohttp import web
from aiohttp.typedefs import Handler

from aiohttp_apigami import (
    cookies_schema,
    docs,
    headers_schema,
    json_schema,
    match_info_schema,
    querystring_schema,
    request_schema,
    response_schema,
)
from tests.fixtures.schemas import (
    CookiesSchema,
    HeaderSchema,
    MatchInfoSchema,
    RequestDataclass,
    RequestSchema,
    ResponseDataclass,
    ResponseSchema,
)


@dataclass
class BasicHandlers:
    """Container for basic handler functions."""

    get: Handler
    post: Handler
    post_with_example_to_endpoint: Handler
    post_with_example_to_ref: Handler
    post_partial: Handler
    post_callable_schema: Handler
    other: Handler


@pytest.fixture
def basic_handlers(example_for_request_schema: dict[str, Any]) -> BasicHandlers:
    """Return a dataclass of basic handler functions."""

    @docs(
        tags=["mytag"],
        summary="Test method summary",
        description="Test method description",
        responses={404: {"description": "Not Found"}},
    )
    @request_schema(RequestSchema, location="querystring")
    @response_schema(ResponseSchema, 200, description="Success response")
    async def handler_get(request: web.Request) -> web.Response:
        return web.json_response({"msg": "done", "data": {}})

    @request_schema(RequestSchema)
    async def handler_post(request: web.Request) -> web.Response:
        return web.json_response({"msg": "done", "data": {}})

    @request_schema(RequestSchema, example=example_for_request_schema)
    async def handler_post_with_example_to_endpoint(request: web.Request) -> web.Response:
        return web.json_response({"msg": "done", "data": {}})

    @request_schema(RequestSchema, example=example_for_request_schema, add_to_refs=True)
    async def handler_post_with_example_to_ref(request: web.Request) -> web.Response:
        return web.json_response({"msg": "done", "data": {}})

    @request_schema(RequestSchema(partial=True))
    async def handler_post_partial(request: web.Request) -> web.Response:
        return web.json_response({"msg": "done", "data": {}})

    @request_schema(RequestSchema())
    async def handler_post_callable_schema(request: web.Request) -> web.Response:
        return web.json_response({"msg": "done", "data": {}})

    async def other(request: web.Request) -> web.Response:
        return web.Response()

    return BasicHandlers(
        get=handler_get,
        post=handler_post,
        post_with_example_to_endpoint=handler_post_with_example_to_endpoint,
        post_with_example_to_ref=handler_post_with_example_to_ref,
        post_partial=handler_post_partial,
        post_callable_schema=handler_post_callable_schema,
        other=other,
    )


@dataclass
class EchoHandlers:
    """Container for echo handler functions."""

    post: Handler
    get: Handler


@pytest.fixture
def echo_handlers() -> EchoHandlers:
    """Return handlers that echo back the data they receive."""

    @request_schema(RequestSchema)
    async def handler_post_echo(request: web.Request) -> web.Response:
        return web.json_response(request["data"])

    @request_schema(RequestSchema, location="querystring")
    async def handler_get_echo(request: web.Request) -> web.Response:
        return web.json_response(request["data"])

    return EchoHandlers(
        post=handler_post_echo,
        get=handler_get_echo,
    )


@pytest.fixture
def variable_handler() -> Handler:
    """Return a handler that works with path variables."""

    @docs(
        parameters=[
            {
                "in": "path",
                "name": "var",
                "schema": {"type": "string", "format": "uuid"},
            }
        ]
    )
    async def handler_get_variable(request: web.Request) -> web.Response:
        return web.json_response(request["data"])

    return handler_get_variable


@pytest.fixture
def validated_view() -> Handler:
    """Return a handler that validates multiple request parts."""

    @match_info_schema(MatchInfoSchema)
    @querystring_schema(RequestSchema)
    @json_schema(RequestSchema)
    @headers_schema(HeaderSchema)
    @cookies_schema(CookiesSchema)
    async def validated_view(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "json": request["json"],
                "headers": request["headers"],
                "cookies": request["cookies"],
                "match_info": request["match_info"],
                "querystring": request["querystring"],
            }
        )

    return validated_view


@pytest.fixture
def dataclass_handler() -> Handler:
    """Return a handler that works with dataclasses."""

    @docs(
        tags=["dataclass"],
        summary="Test dataclass handler",
        description="Test handler using dataclasses",
    )
    @request_schema(RequestDataclass, location="json")
    @response_schema(ResponseDataclass, 200, description="Success response with dataclass")
    async def handler_dataclass(request: web.Request) -> web.Response:
        # Access data as a dataclass instance
        data: RequestDataclass = request["data"]
        return web.json_response(
            {"msg": "done", "data": {"id": data.id, "name": data.name, "is_active": data.bool_field}}
        )

    return handler_dataclass


@pytest.fixture
def class_based_view() -> type[web.View]:
    """Return a class-based view."""

    class ViewClass(web.View):
        @docs(
            tags=["mytag"],
            summary="View method summary",
            description="View method description",
        )
        @request_schema(RequestSchema, location="querystring")
        async def get(self) -> web.Response:
            return web.json_response(self.request["data"])

        async def delete(self) -> web.Response:
            return web.json_response({"hello": "world"})

    return ViewClass
