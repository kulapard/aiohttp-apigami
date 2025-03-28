"""Pytest configuration file."""
# ruff: noqa: F401, F403

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient
from aiohttp.typedefs import Handler, Middleware
from pytest_aiohttp.plugin import AiohttpClient

from aiohttp_apigami import setup_aiohttp_apispec, validation_middleware
from aiohttp_apigami.typedefs import ErrorHandler

# Import all fixtures - fixture modules import our handler classes
from tests.fixtures import *
from tests.fixtures.handlers import BasicHandlers, EchoHandlers


@pytest.fixture(params=[True, False])
def nested_param(request: pytest.FixtureRequest) -> bool:
    """Parametrize tests to run with both nested and flat app structures."""
    return bool(request.param)


@pytest.fixture
async def aiohttp_app(
    aiohttp_client: AiohttpClient,
    basic_handlers: BasicHandlers,
    echo_handlers: EchoHandlers,
    variable_handler: Handler,
    validated_view: Handler,
    dataclass_handler: Handler,
    class_based_view: type[web.View],
    error_handler: ErrorHandler,
    nested_param: bool,
    error_middleware: Middleware,
) -> TestClient[web.Request, web.Application]:
    """Return a client for a basic application with all handlers."""
    app = web.Application()

    if nested_param:
        # Create a nested app structure with a v1 subapp
        v1 = web.Application()

        # Set up API docs in the v1 subapp
        setup_aiohttp_apispec(
            app=v1,
            title="API documentation",
            version="0.0.1",
            url="/api/docs/api-docs",
            swagger_path="/api/docs",
            error_callback=error_handler,
        )

        # Add middlewares to the v1 subapp
        v1.middlewares.extend([error_middleware, validation_middleware])

        # Add routes to the v1 subapp
        v1.router.add_routes(
            [
                web.get("/test", basic_handlers.get),
                web.post("/test", basic_handlers.post),
                web.post("/example_endpoint", basic_handlers.post_with_example_to_endpoint),
                web.post("/example_ref", basic_handlers.post_with_example_to_ref),
                web.post("/test_partial", basic_handlers.post_partial),
                web.post("/test_call", basic_handlers.post_callable_schema),
                web.get("/other", basic_handlers.other),
                web.get("/echo", echo_handlers.get),
                web.view("/class_echo", class_based_view),
                web.post("/echo", echo_handlers.post),
                web.get("/variable/{var}", variable_handler),
                web.post("/validate/{uuid}", validated_view),
                web.post("/dataclass", dataclass_handler),
            ]
        )

        # Add the v1 subapp to the main app
        app.add_subapp("/v1/", v1)
    else:
        # Set up API docs in the main app
        setup_aiohttp_apispec(
            app=app,
            url="/v1/api/docs/api-docs",
            swagger_path="/v1/api/docs",
            error_callback=error_handler,
        )

        # Add middlewares to the main app
        app.middlewares.extend([error_middleware, validation_middleware])

        # Add routes to the main app
        app.router.add_routes(
            [
                web.get("/v1/test", basic_handlers.get),
                web.post("/v1/test", basic_handlers.post),
                web.post("/v1/example_endpoint", basic_handlers.post_with_example_to_endpoint),
                web.post("/v1/example_ref", basic_handlers.post_with_example_to_ref),
                web.post("/v1/test_partial", basic_handlers.post_partial),
                web.post("/v1/test_call", basic_handlers.post_callable_schema),
                web.get("/v1/other", basic_handlers.other),
                web.get("/v1/echo", echo_handlers.get),
                web.view("/v1/class_echo", class_based_view),
                web.post("/v1/echo", echo_handlers.post),
                web.get("/v1/variable/{var}", variable_handler),
                web.post("/v1/validate/{uuid}", validated_view),
                web.post("/v1/dataclass", dataclass_handler),
            ]
        )

    return await aiohttp_client(app)
