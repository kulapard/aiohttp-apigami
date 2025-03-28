from typing import Any
from unittest.mock import patch

import pytest
from aiohttp import web
from aiohttp.typedefs import Handler
from marshmallow import Schema

from aiohttp_apigami import docs, request_schema, response_schema
from aiohttp_apigami.validation import ValidationSchema
from tests.fixtures import RequestDataclass, ResponseDataclass


@pytest.fixture
def aiohttp_view_dataclass_request() -> Handler:
    @request_schema(RequestDataclass, location="json")
    async def index(request: web.Request, **data: Any) -> web.Response:
        return web.json_response({"msg": "done", "data": {}})

    return index


@pytest.fixture
def aiohttp_view_dataclass_response() -> Handler:
    @response_schema(ResponseDataclass, 200, description="Dataclass response")
    async def index(request: web.Request, **data: Any) -> web.Response:
        return web.json_response({"msg": "done", "data": {}})

    return index


@pytest.fixture
def aiohttp_view_dataclass_all() -> Handler:
    @docs(
        tags=["dataclass"],
        summary="Dataclass test",
        description="Testing dataclass integration",
    )
    @request_schema(RequestDataclass, location="json")
    @response_schema(ResponseDataclass, 200, description="Success response")
    async def index(request: web.Request, **data: Any) -> web.Response:
        return web.json_response({"msg": "done", "data": {}})

    return index


@pytest.fixture
def example_for_request_dataclass() -> dict[str, Any]:
    return {
        "id": 1,
        "name": "test",
        "bool_field": True,
        "list_field": [1, 2, 3],
        "nested_field": {"i": 12},
    }


@pytest.fixture
def aiohttp_view_dataclass_request_with_example(example_for_request_dataclass: dict[str, Any]) -> Handler:
    @request_schema(RequestDataclass, example=example_for_request_dataclass, add_to_refs=True)
    async def index(request: web.Request, **data: Any) -> web.Response:
        return web.json_response({"msg": "done", "data": {}})

    return index


def test_dataclass_request_schema_view(aiohttp_view_dataclass_request: Handler) -> None:
    """Test request_schema with a dataclass."""
    assert hasattr(aiohttp_view_dataclass_request, "__apispec__")
    assert hasattr(aiohttp_view_dataclass_request, "__schemas__")
    assert len(aiohttp_view_dataclass_request.__schemas__) == 1
    schema = aiohttp_view_dataclass_request.__schemas__[0]
    assert isinstance(schema, ValidationSchema)
    assert schema.location == "json"
    assert schema.put_into is None

    # Check that the schema has been converted to a marshmallow schema

    assert isinstance(schema.schema, Schema)

    # Verify fields were preserved
    fields_dict = schema.schema.fields
    assert "id" in fields_dict
    assert "name" in fields_dict
    assert "bool_field" in fields_dict
    assert "list_field" in fields_dict
    assert "nested_field" in fields_dict


def test_dataclass_response_schema_view(aiohttp_view_dataclass_response: Handler) -> None:
    """Test response_schema with a dataclass."""
    assert hasattr(aiohttp_view_dataclass_response, "__apispec__")
    assert "200" in aiohttp_view_dataclass_response.__apispec__["responses"]
    response_spec = aiohttp_view_dataclass_response.__apispec__["responses"]["200"]
    assert response_spec["description"] == "Dataclass response"
    assert "schema" in response_spec

    # Check that schema is converted to a marshmallow schema

    assert isinstance(response_spec["schema"], Schema)


def test_dataclass_with_example(
    aiohttp_view_dataclass_request_with_example: Handler, example_for_request_dataclass: dict[str, Any]
) -> None:
    """Test request_schema with a dataclass and example."""
    assert hasattr(aiohttp_view_dataclass_request_with_example, "__apispec__")
    schema = aiohttp_view_dataclass_request_with_example.__apispec__["schemas"][0]
    expected_result = example_for_request_dataclass.copy()
    expected_result["add_to_refs"] = True
    assert schema["example"] == expected_result


def test_dataclass_all(aiohttp_view_dataclass_all: Handler) -> None:
    """Test using all decorators with dataclasses."""
    assert hasattr(aiohttp_view_dataclass_all, "__apispec__")
    assert hasattr(aiohttp_view_dataclass_all, "__schemas__")

    # Check docs
    assert aiohttp_view_dataclass_all.__apispec__["tags"] == ["dataclass"]
    assert aiohttp_view_dataclass_all.__apispec__["summary"] == "Dataclass test"
    assert aiohttp_view_dataclass_all.__apispec__["description"] == "Testing dataclass integration"

    # Check request schema
    assert len(aiohttp_view_dataclass_all.__schemas__) == 1
    schema = aiohttp_view_dataclass_all.__schemas__[0]
    assert isinstance(schema, ValidationSchema)
    assert schema.location == "json"

    # Check that schema has been converted to a marshmallow schema

    assert isinstance(schema.schema, Schema)

    # Verify request fields were preserved
    fields_dict = schema.schema.fields
    assert "id" in fields_dict
    assert "name" in fields_dict
    assert "bool_field" in fields_dict
    assert "list_field" in fields_dict
    assert "nested_field" in fields_dict

    # Check response schema
    assert "200" in aiohttp_view_dataclass_all.__apispec__["responses"]
    response_spec = aiohttp_view_dataclass_all.__apispec__["responses"]["200"]
    assert response_spec["description"] == "Success response"
    assert "schema" in response_spec
    assert isinstance(response_spec["schema"], Schema)

    # Verify response fields were preserved
    response_fields = response_spec["schema"].fields
    assert "msg" in response_fields
    assert "data" in response_fields


@patch("aiohttp_apigami.utils.mr", None)
def test_dataclass_without_marshmallow_recipe() -> None:
    """Test decorators with dataclass when marshmallow-recipe is not available."""
    with pytest.raises(RuntimeError, match="marshmallow-recipe is required for dataclass support"):

        @request_schema(RequestDataclass)
        async def handler(request: web.Request) -> web.Response:
            return web.json_response({})

    with pytest.raises(RuntimeError, match="marshmallow-recipe is required for dataclass support"):

        @response_schema(ResponseDataclass, 200)
        async def handler2(request: web.Request) -> web.Response:
            return web.json_response({})
