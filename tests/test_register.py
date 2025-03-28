import pytest
from aiohttp import web

from aiohttp_apigami import AiohttpApiSpec, docs, request_schema, setup_aiohttp_apispec
from aiohttp_apigami.constants import APISPEC_PARSER, APISPEC_VALIDATED_DATA_NAME
from aiohttp_apigami.core import OpenApiVersion
from aiohttp_apigami.swagger_ui import NAME_SWAGGER_SPEC
from tests.fixtures.schemas import RequestSchema


@pytest.mark.asyncio
async def test_register_basic() -> None:
    """Test basic registration of API spec."""
    app = web.Application()
    api_spec = AiohttpApiSpec(title="Test API", version="1.0.0")

    # Initial state should be not registered
    assert api_spec._registered is False

    # Register the API spec
    api_spec.register(app)

    # Should be marked as registered
    assert api_spec._registered is True

    # Check app configuration
    assert app[APISPEC_VALIDATED_DATA_NAME] == api_spec._request_data_name
    assert APISPEC_PARSER in app

    # Check that the swagger spec route was added
    routes = {route.name: route for route in app.router.routes() if route.name is not None}
    assert NAME_SWAGGER_SPEC in routes


@pytest.mark.asyncio
async def test_register_twice() -> None:
    """Test that register can't be called twice."""
    app = web.Application()
    api_spec = AiohttpApiSpec(title="Test API", version="1.0.0")

    # First registration should work
    api_spec.register(app)
    assert api_spec._registered is True

    # Get initial route count
    initial_route_count = len(app.router.routes())

    # Second registration should be skipped
    api_spec.register(app)

    # Route count should remain the same
    assert len(app.router.routes()) == initial_route_count


@pytest.mark.asyncio
async def test_register_with_custom_url() -> None:
    """Test registration with custom URL."""
    app = web.Application()
    custom_url = "/custom/swagger.json"
    api_spec = AiohttpApiSpec(url=custom_url, title="Test API", version="1.0.0")

    # Register the API spec
    api_spec.register(app)

    # Check that custom URL is used
    routes = {route.name: route for route in app.router.routes() if route.name is not None}
    assert NAME_SWAGGER_SPEC in routes

    # Verify the route has our custom path
    route = routes[NAME_SWAGGER_SPEC]
    assert str(route.url_for()).endswith("swagger.json")
    assert "/custom/" in str(route.url_for())


@pytest.mark.asyncio
async def test_register_with_swagger_path() -> None:
    """Test registration with swagger UI path."""
    app = web.Application()
    swagger_path = "/docs"
    api_spec = AiohttpApiSpec(title="Test API", version="1.0.0", swagger_path=swagger_path)

    # Register the API spec
    api_spec.register(app)

    # Should set up swagger UI - verify swagger docs route exists
    route_names = [route.name for route in app.router.routes() if route.name is not None]
    assert "swagger.docs" in route_names

    # Check if static route was added
    assert "swagger.static" in route_names


@pytest.mark.asyncio
async def test_register_with_empty_url() -> None:
    """Test registration with empty URL (no swagger spec endpoint)."""
    app = web.Application()
    api_spec = AiohttpApiSpec(url="", title="Test API", version="1.0.0")

    # Initial route count
    initial_route_count = len(app.router.routes())

    # Register the API spec
    api_spec.register(app)

    # Should be marked as registered
    assert api_spec._registered is True

    # Should not have added any routes for swagger spec
    assert len(app.router.routes()) == initial_route_count


@pytest.mark.asyncio
async def test_register_with_error_callback() -> None:
    """Test registration with custom error callback."""
    app = web.Application()

    def error_callback(*args: object, **kwargs: object) -> None:
        pass

    api_spec = AiohttpApiSpec(title="Test API", version="1.0.0", error_callback=error_callback)

    # Register the API spec
    api_spec.register(app)

    # Parser should have our error callback
    assert app[APISPEC_PARSER].error_callback == error_callback


@pytest.mark.asyncio
async def test_register_in_place_vs_on_startup() -> None:
    """Test in_place vs on_startup registration modes."""
    # Test in_place=True
    app_in_place = web.Application()
    api_spec_in_place = AiohttpApiSpec(title="Test API", version="1.0.0", in_place=True)

    api_spec_in_place.register(app_in_place)

    # Should have registered the routes directly
    assert api_spec_in_place._registered is True

    # Test in_place=False
    app_on_startup = web.Application()
    api_spec_on_startup = AiohttpApiSpec(title="Test API", version="1.0.0", in_place=False)

    api_spec_on_startup.register(app_on_startup)

    # Should have registered a startup handler
    # Application could have default handlers, so check if size increased
    assert len(app_on_startup.on_startup) > 0

    # Verify the last handler is our _async_register function
    last_handler = app_on_startup.on_startup[-1]
    assert last_handler.__name__ == "_async_register"

    # Should still be marked as registered
    assert api_spec_on_startup._registered is True


@pytest.mark.asyncio
async def test_register_with_openapi_v3() -> None:
    """Test registration with OpenAPI v3."""
    app = web.Application()
    api_spec = AiohttpApiSpec(title="Test API", version="1.0.0", openapi_version=OpenApiVersion.V303, in_place=True)

    # Register the API spec
    api_spec.register(app)

    # Call the method directly to test OpenAPI version
    swagger_dict = api_spec.swagger_dict()
    assert swagger_dict["openapi"] == "3.0.3"

    # In OpenAPI v3, there should be no "swagger" field
    assert "swagger" not in swagger_dict


@pytest.mark.asyncio
async def test_setup_aiohttp_apispec_in_place() -> None:
    """Test that in_place parameter controls when routes are registered."""
    # Test with in_place=True: routes should be registered immediately
    app_in_place = web.Application()

    # Add a test route with docs decorator
    @docs(
        tags=["test"],
        summary="Test endpoint",
        description="Test description",
    )
    async def test_handler(request: web.Request) -> web.Response:
        return web.Response(text="test")

    app_in_place.router.add_get("/test", test_handler)

    # Setup API spec with in_place=True
    setup_aiohttp_apispec(
        app=app_in_place,
        title="Test API",
        version="1.0.0",
        in_place=True,
    )

    # Swagger dictionary should be available immediately
    assert "swagger_dict" in app_in_place
    assert "paths" in app_in_place["swagger_dict"]
    assert "/test" in app_in_place["swagger_dict"]["paths"]
    assert "get" in app_in_place["swagger_dict"]["paths"]["/test"]

    # Verify docs info was captured
    test_info = app_in_place["swagger_dict"]["paths"]["/test"]["get"]
    assert test_info["tags"] == ["test"]
    assert test_info["summary"] == "Test endpoint"
    assert test_info["description"] == "Test description"

    # Test with in_place=False: routes should be registered only on startup
    app_on_startup = web.Application()

    # Add a test route
    app_on_startup.router.add_get("/test", test_handler)

    # Setup API spec with in_place=False
    setup_aiohttp_apispec(
        app=app_on_startup,
        title="Test API",
        version="1.0.0",
        in_place=False,
    )

    # Swagger dictionary should not be available yet
    assert "swagger_dict" not in app_on_startup

    # Manually trigger on_startup event handlers
    for handler in app_on_startup.on_startup:
        await handler(app_on_startup)

    # Now swagger dictionary should be available
    assert "swagger_dict" in app_on_startup
    assert "paths" in app_on_startup["swagger_dict"]
    assert "/test" in app_on_startup["swagger_dict"]["paths"]
    assert "get" in app_on_startup["swagger_dict"]["paths"]["/test"]


@pytest.mark.asyncio
async def test_setup_aiohttp_apispec_with_decorated_handlers() -> None:
    """Test that in_place parameter works with decorated handlers."""
    # Create two separate apps to test both in_place modes
    app_in_place = web.Application()
    app_on_startup = web.Application()

    # Define a handler with API decorators
    @docs(
        tags=["test"],
        summary="Test endpoint",
        description="Test description",
    )
    @request_schema(RequestSchema)
    async def decorated_handler(request: web.Request) -> web.Response:
        return web.Response(text="test")

    # Add the handler to both apps
    app_in_place.router.add_post("/decorated", decorated_handler)
    app_on_startup.router.add_post("/decorated", decorated_handler)

    # Setup API spec with in_place=True
    setup_aiohttp_apispec(
        app=app_in_place,
        title="Test API",
        version="1.0.0",
        in_place=True,
    )

    # Setup API spec with in_place=False
    setup_aiohttp_apispec(
        app=app_on_startup,
        title="Test API",
        version="1.0.0",
        in_place=False,
    )

    # For in_place=True, swagger dict should be available immediately
    # and should contain the decorated endpoint
    assert "swagger_dict" in app_in_place
    assert "/decorated" in app_in_place["swagger_dict"]["paths"]
    decorated_path = app_in_place["swagger_dict"]["paths"]["/decorated"]
    assert "post" in decorated_path
    assert decorated_path["post"]["tags"] == ["test"]
    assert decorated_path["post"]["summary"] == "Test endpoint"
    assert decorated_path["post"]["description"] == "Test description"

    # For in_place=False, swagger dict should not be available yet
    assert "swagger_dict" not in app_on_startup

    # Manually trigger on_startup event handlers
    for handler in app_on_startup.on_startup:
        await handler(app_on_startup)

    # Now swagger dict should be available and should contain the decorated endpoint
    assert "swagger_dict" in app_on_startup
    assert "/decorated" in app_on_startup["swagger_dict"]["paths"]
    decorated_path = app_on_startup["swagger_dict"]["paths"]["/decorated"]
    assert "post" in decorated_path
    assert decorated_path["post"]["tags"] == ["test"]
    assert decorated_path["post"]["summary"] == "Test endpoint"
    assert decorated_path["post"]["description"] == "Test description"


@pytest.mark.asyncio
async def test_setup_aiohttp_apispec_with_subapps() -> None:
    """Test that in_place parameter works with nested application structure."""
    # Create main apps for both in_place modes
    main_app_in_place = web.Application()
    main_app_on_startup = web.Application()

    # Create subapps
    sub_app_in_place = web.Application()
    sub_app_on_startup = web.Application()

    # Define handlers with API decorators
    @docs(
        tags=["subapp"],
        summary="Subapp endpoint",
        description="Test endpoint in subapp",
    )
    @request_schema(RequestSchema)
    async def sub_handler(request: web.Request) -> web.Response:
        return web.Response(text="subapp test")

    @docs(
        tags=["new"],
        summary="New endpoint",
        description="Endpoint added before setup",
    )
    async def new_handler(request: web.Request) -> web.Response:
        return web.Response(text="new endpoint")

    # Add the handlers to both subapps
    sub_app_in_place.router.add_get("/subtest", sub_handler)
    sub_app_on_startup.router.add_get("/subtest", sub_handler)

    # Add the new handler only to in_place subapp to demonstrate
    # that all routes registered before setup are included
    sub_app_in_place.router.add_get("/new", new_handler)

    # Setup API specs BEFORE adding the subapps to main apps
    # Setup API spec with in_place=True for subapp
    setup_aiohttp_apispec(
        app=sub_app_in_place,
        title="Test Subapp API",
        version="1.0.0",
        in_place=True,
        url="/api/docs/swagger.json",  # Set a unique URL to avoid conflicts
    )

    # Setup API spec with in_place=False for other subapp
    setup_aiohttp_apispec(
        app=sub_app_on_startup,
        title="Test Subapp API",
        version="1.0.0",
        in_place=False,
        url="/api/docs/swagger2.json",  # Set a unique URL to avoid conflicts
    )

    # Now add subapps to main apps
    main_app_in_place.add_subapp("/api/v1/", sub_app_in_place)
    main_app_on_startup.add_subapp("/api/v1/", sub_app_on_startup)

    # For in_place=True, swagger dict should be available immediately in subapp
    assert "swagger_dict" in sub_app_in_place
    # For subapps, we should check for the path without the prefix since
    # the prefix is only applied when the subapp is added to the main app
    assert "/subtest" in sub_app_in_place["swagger_dict"]["paths"]

    # Verify that the new route is also documented
    assert "/new" in sub_app_in_place["swagger_dict"]["paths"]

    # Verify documentation details for in_place=True
    subtest_path_in_place = sub_app_in_place["swagger_dict"]["paths"]["/subtest"]
    assert "get" in subtest_path_in_place
    assert subtest_path_in_place["get"]["tags"] == ["subapp"]
    assert subtest_path_in_place["get"]["summary"] == "Subapp endpoint"
    assert subtest_path_in_place["get"]["description"] == "Test endpoint in subapp"

    # Also verify schema was properly registered
    assert "parameters" in subtest_path_in_place["get"]
    schema_param = subtest_path_in_place["get"]["parameters"][0]
    assert schema_param["in"] == "body"
    assert schema_param["schema"]["$ref"] == "#/definitions/Request"

    # Check title and version
    assert sub_app_in_place["swagger_dict"]["info"]["title"] == "Test Subapp API"
    assert sub_app_in_place["swagger_dict"]["info"]["version"] == "1.0.0"

    # For in_place=False, swagger dict should not be available yet
    assert "swagger_dict" not in sub_app_on_startup

    # Simulate app startup
    # First start the main app
    for handler in main_app_on_startup.on_startup:
        await handler(main_app_on_startup)

    # Then start the subapp
    for handler in sub_app_on_startup.on_startup:
        await handler(sub_app_on_startup)

    # Now swagger dict should be available in the subapp
    assert "swagger_dict" in sub_app_on_startup

    # The path in the swagger dict should include the prefix from the main app
    # because routes are registered during startup after the subapp is added
    assert "/api/v1/subtest" in sub_app_on_startup["swagger_dict"]["paths"]

    # Verify the documentation was correctly generated
    subtest_path = sub_app_on_startup["swagger_dict"]["paths"]["/api/v1/subtest"]
    assert "get" in subtest_path
    assert subtest_path["get"]["tags"] == ["subapp"]
    assert subtest_path["get"]["summary"] == "Subapp endpoint"

    # Document what we would have tested if we could add a route after freezing
    # NOTE: Adding new routes after application is frozen is not possible
    # If a new route needs to be added after setup:
    # 1. Either use in_place=False to register routes on startup
    # 2. Or manually re-register all routes by calling setup again
