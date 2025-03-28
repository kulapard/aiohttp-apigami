import pytest
from aiohttp import web

from aiohttp_apigami import (
    cookies_schema,
    form_schema,
    headers_schema,
    json_schema,
    match_info_schema,
    querystring_schema,
    request_schema,
)
from aiohttp_apigami.decorators.request import VALID_SCHEMA_LOCATIONS
from tests.fixtures.schemas import RequestSchema


class TestInvalidLocations:
    """Test that decorators properly validate location parameters."""

    @pytest.mark.parametrize(
        "invalid_location",
        [
            "invalid",
            "body",  # common mistake from other frameworks
            "params",  # common mistake from other frameworks
            "query_params",  # common mistake from other frameworks
            "",  # empty string
            "JSON",  # case sensitive - only lowercase allowed
            " json",  # no spaces allowed
            "json ",  # no spaces allowed
            123,  # must be string, not int
            None,  # must be string, not None
        ],
    )
    def test_request_schema_with_invalid_location(self, invalid_location: str) -> None:
        """Test that request_schema raises ValueError with invalid location."""
        with pytest.raises(ValueError) as exc_info:

            @request_schema(RequestSchema, location=invalid_location)  # type: ignore[arg-type]
            async def handler(request: web.Request) -> web.Response:
                return web.json_response({})

        assert str(exc_info.value) == f"Invalid location argument: {invalid_location}"

    def test_shorthand_decorators_with_invalid_location_params(self) -> None:
        """
        Test that trying to pass an extra location parameter to a shorthand decorator
        still validates locations.

        When a shorthand decorator is used, its parameters are validated at the time
        the decorator is applied to a function, not when the decorator is created via partial.
        """
        with pytest.raises(ValueError) as exc_info:
            # This would create a call like request_schema(RequestSchema, location="json", location="invalid")
            @json_schema(RequestSchema, location="invalid")  # type: ignore[arg-type]
            async def handler_json(request: web.Request) -> web.Response:
                return web.json_response({})

        assert "Invalid location argument: invalid" in str(exc_info.value)

        # Do the same test with a few more decorators to be thorough
        with pytest.raises(ValueError) as exc_info:

            @querystring_schema(RequestSchema, location="invalid")  # type: ignore[arg-type]
            async def handler_qs(request: web.Request) -> web.Response:
                return web.json_response({})

        assert "Invalid location argument: invalid" in str(exc_info.value)


class TestValidLocations:
    @pytest.mark.parametrize("valid_location", list(VALID_SCHEMA_LOCATIONS))
    def test_request_schema_with_valid_location(self, valid_location: str) -> None:
        """Test that request_schema works with all valid locations."""

        @request_schema(RequestSchema, location=valid_location)  # type: ignore[arg-type]
        async def handler(request: web.Request) -> web.Response:
            return web.json_response({})

        assert hasattr(handler, "__apispec__")
        assert hasattr(handler, "__schemas__")
        schema_info = handler.__apispec__["schemas"][0]
        assert schema_info["location"] == valid_location

    def test_shorthand_decorators_correct_location(self) -> None:
        """Test that each shorthand decorator sets the correct location."""

        @json_schema(RequestSchema)
        async def handler_json(request: web.Request) -> web.Response:
            return web.json_response({})

        assert hasattr(handler_json, "__apispec__")
        assert hasattr(handler_json, "__schemas__")
        assert handler_json.__apispec__["schemas"][0]["location"] == "json"
        assert handler_json.__schemas__[0].location == "json"
        assert handler_json.__schemas__[0].put_into == "json"

        @querystring_schema(RequestSchema)
        async def handler_qs(request: web.Request) -> web.Response:
            return web.json_response({})

        assert hasattr(handler_qs, "__apispec__")
        assert hasattr(handler_qs, "__schemas__")
        assert handler_qs.__apispec__["schemas"][0]["location"] == "querystring"
        assert handler_qs.__schemas__[0].location == "querystring"
        assert handler_qs.__schemas__[0].put_into == "querystring"

        @match_info_schema(RequestSchema)
        async def handler_mi(request: web.Request) -> web.Response:
            return web.json_response({})

        assert hasattr(handler_mi, "__apispec__")
        assert hasattr(handler_mi, "__schemas__")
        assert handler_mi.__apispec__["schemas"][0]["location"] == "match_info"
        assert handler_mi.__schemas__[0].location == "match_info"
        assert handler_mi.__schemas__[0].put_into == "match_info"

        @headers_schema(RequestSchema)
        async def handler_headers(request: web.Request) -> web.Response:
            return web.json_response({})

        assert hasattr(handler_headers, "__apispec__")
        assert hasattr(handler_headers, "__schemas__")
        assert handler_headers.__apispec__["schemas"][0]["location"] == "headers"
        assert handler_headers.__schemas__[0].location == "headers"
        assert handler_headers.__schemas__[0].put_into == "headers"

        @cookies_schema(RequestSchema)
        async def handler_cookies(request: web.Request) -> web.Response:
            return web.json_response({})

        assert hasattr(handler_cookies, "__apispec__")
        assert hasattr(handler_cookies, "__schemas__")
        assert handler_cookies.__apispec__["schemas"][0]["location"] == "cookies"
        assert handler_cookies.__schemas__[0].location == "cookies"
        assert handler_cookies.__schemas__[0].put_into == "cookies"

        @form_schema(RequestSchema)
        async def handler_form(request: web.Request) -> web.Response:
            return web.json_response({})

        assert hasattr(handler_form, "__apispec__")
        assert hasattr(handler_form, "__schemas__")
        assert handler_form.__apispec__["schemas"][0]["location"] == "form"
        assert handler_form.__schemas__[0].location == "form"
        assert handler_form.__schemas__[0].put_into == "form"
