import pytest
from aiohttp import web

from aiohttp_apigami import AiohttpApiSpec
from aiohttp_apigami.constants import APISPEC_PARSER, APISPEC_VALIDATED_DATA_NAME
from aiohttp_apigami.core import OpenApiVersion
from aiohttp_apigami.swagger_ui import NAME_SWAGGER_SPEC


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
