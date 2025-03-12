from typing import Any

import pytest
from aiohttp import web
from aiohttp.typedefs import Handler
from marshmallow import Schema, fields

from apispec_aiohttp import docs, request_schema, response_schema
from apispec_aiohttp.aiohttp import HandlerSchema


class RequestSchema(Schema):
    id = fields.Int()
    name = fields.Str(metadata={"description": "name"})
    bool_field = fields.Bool()
    list_field = fields.List(fields.Int())


class ResponseSchema(Schema):
    msg = fields.Str()
    data = fields.Dict()


class TestViewDecorators:
    @pytest.fixture
    def aiohttp_view_all(self) -> Handler:
        @docs(
            tags=["mytag"],
            summary="Test method summary",
            description="Test method description",
        )
        @request_schema(RequestSchema, location="querystring")
        @response_schema(ResponseSchema, 200)
        async def index(request: web.Request, **data: Any) -> web.Response:
            return web.json_response({"msg": "done", "data": {}})

        return index

    @pytest.fixture
    def aiohttp_view_docs(self) -> Handler:
        @docs(
            tags=["mytag"],
            summary="Test method summary",
            description="Test method description",
        )
        async def index(request: web.Request, **data: Any) -> web.Response:
            return web.json_response({"msg": "done", "data": {}})

        return index

    @pytest.fixture
    def aiohttp_view_kwargs(self) -> Handler:
        @request_schema(RequestSchema, location="querystring")
        async def index(request: web.Request, **data: Any) -> web.Response:
            return web.json_response({"msg": "done", "data": {}})

        return index

    @pytest.fixture
    def aiohttp_view_marshal(self) -> Handler:
        @response_schema(ResponseSchema, 200, description="Method description")
        async def index(request: web.Request, **data: Any) -> web.Response:
            return web.json_response({"msg": "done", "data": {}})

        return index

    @pytest.fixture
    def aiohttp_view_request_schema_with_example_without_refs(
        self, example_for_request_schema: dict[str, Any]
    ) -> Handler:
        @request_schema(RequestSchema, example=example_for_request_schema)
        async def index(request: web.Request, **data: Any) -> web.Response:
            return web.json_response({"msg": "done", "data": {}})

        return index

    @pytest.fixture
    def aiohttp_view_request_schema_with_example(self, example_for_request_schema: dict[str, Any]) -> Handler:
        @request_schema(RequestSchema, example=example_for_request_schema, add_to_refs=True)
        async def index(request: web.Request, **data: Any) -> web.Response:
            return web.json_response({"msg": "done", "data": {}})

        return index

    def test_docs_view(self, aiohttp_view_docs: Handler) -> None:
        assert hasattr(aiohttp_view_docs, "__apispec__")
        assert aiohttp_view_docs.__apispec__["tags"] == ["mytag"]
        assert aiohttp_view_docs.__apispec__["summary"] == "Test method summary"
        assert aiohttp_view_docs.__apispec__["description"] == "Test method description"
        for param in ("parameters", "responses"):
            assert param in aiohttp_view_docs.__apispec__

    def test_request_schema_view(self, aiohttp_view_kwargs: Handler) -> None:
        assert hasattr(aiohttp_view_kwargs, "__apispec__")
        assert hasattr(aiohttp_view_kwargs, "__schemas__")
        assert len(aiohttp_view_kwargs.__schemas__) == 1
        schema = aiohttp_view_kwargs.__schemas__[0]
        assert isinstance(schema, HandlerSchema)
        assert isinstance(schema.schema, RequestSchema)
        assert schema.location == "querystring"
        assert schema.put_into is None
        for param in ("parameters", "responses"):
            assert param in aiohttp_view_kwargs.__apispec__

    @pytest.mark.skip(reason="__apispec__ is not filled before starting the aiohttp server")
    def test_request_schema_parameters(self, aiohttp_view_kwargs: Handler) -> None:
        assert hasattr(aiohttp_view_kwargs, "__apispec__")
        parameters = aiohttp_view_kwargs.__apispec__["parameters"]
        assert sorted(parameters, key=lambda x: x["name"]) == [
            {"in": "query", "name": "bool_field", "required": False, "type": "boolean"},
            {
                "in": "query",
                "name": "id",
                "required": False,
                "type": "integer",
                "format": "int32",
            },
            {
                "in": "query",
                "name": "list_field",
                "required": False,
                "collectionFormat": "multi",
                "type": "array",
                "items": {"type": "integer", "format": "int32"},
            },
            {
                "in": "query",
                "name": "name",
                "required": False,
                "type": "string",
                "description": "name",
            },
        ]

    def test_marshalling(self, aiohttp_view_marshal: Handler) -> None:
        assert hasattr(aiohttp_view_marshal, "__apispec__")
        for param in ("parameters", "responses"):
            assert param in aiohttp_view_marshal.__apispec__
        assert "200" in aiohttp_view_marshal.__apispec__["responses"]

    def test_request_schema_with_example_without_refs(
        self,
        aiohttp_view_request_schema_with_example_without_refs: Handler,
        example_for_request_schema: dict[str, Any],
    ) -> None:
        assert hasattr(aiohttp_view_request_schema_with_example_without_refs, "__apispec__")
        schema = aiohttp_view_request_schema_with_example_without_refs.__apispec__["schemas"][0]
        expacted_result = example_for_request_schema.copy()
        expacted_result["add_to_refs"] = False
        assert schema["example"] == expacted_result

    def test_request_schema_with_example(
        self, aiohttp_view_request_schema_with_example: Handler, example_for_request_schema: dict[str, Any]
    ) -> None:
        assert hasattr(aiohttp_view_request_schema_with_example, "__apispec__")
        schema = aiohttp_view_request_schema_with_example.__apispec__["schemas"][0]
        expacted_result = example_for_request_schema.copy()
        expacted_result["add_to_refs"] = True
        assert schema["example"] == expacted_result

    def test_all(self, aiohttp_view_all: Handler) -> None:
        assert hasattr(aiohttp_view_all, "__apispec__")
        assert hasattr(aiohttp_view_all, "__schemas__")
        for param in ("parameters", "responses"):
            assert param in aiohttp_view_all.__apispec__
        assert aiohttp_view_all.__apispec__["tags"] == ["mytag"]
        assert aiohttp_view_all.__apispec__["summary"] == "Test method summary"
        assert aiohttp_view_all.__apispec__["description"] == "Test method description"

    @pytest.fixture
    def aiohttp_view_extended_docs(self) -> Handler:
        security_requirement: list[dict[str, list[str]]] = [{"api_key": []}]

        @docs(
            tags=["extended", "test"],
            summary="Extended docs test",
            description="Testing all parameters of docs decorator",
            parameters=[{"in": "header", "name": "X-Test", "schema": {"type": "string"}}],
            responses={404: {"description": "Not found"}},
            produces=["application/json", "text/html"],
            consumes=["application/json"],
            deprecated=True,
            operation_id="extendedTest",
            security=security_requirement,
            custom_field="custom_value",
        )
        async def index(request: web.Request, **data: Any) -> web.Response:
            return web.json_response({"msg": "done", "data": {}})

        return index

    def test_extended_docs(self, aiohttp_view_extended_docs: Handler) -> None:
        """Test that all typed parameters in docs decorator work correctly."""
        assert hasattr(aiohttp_view_extended_docs, "__apispec__")

        # Test standard parameters
        assert aiohttp_view_extended_docs.__apispec__["tags"] == ["extended", "test"]
        assert aiohttp_view_extended_docs.__apispec__["summary"] == "Extended docs test"
        assert aiohttp_view_extended_docs.__apispec__["description"] == "Testing all parameters of docs decorator"
        assert len(aiohttp_view_extended_docs.__apispec__["parameters"]) == 1
        assert aiohttp_view_extended_docs.__apispec__["parameters"][0]["name"] == "X-Test"
        assert 404 in aiohttp_view_extended_docs.__apispec__["responses"]
        assert aiohttp_view_extended_docs.__apispec__["produces"] == ["application/json", "text/html"]
        assert aiohttp_view_extended_docs.__apispec__["consumes"] == ["application/json"]
        assert aiohttp_view_extended_docs.__apispec__["deprecated"] is True
        # Field name should match what's actually used in the implementation
        assert aiohttp_view_extended_docs.__apispec__["operationId"] == "extendedTest"
        assert aiohttp_view_extended_docs.__apispec__["security"] == [{"api_key": []}]

        # Test custom parameter
        assert aiohttp_view_extended_docs.__apispec__["custom_field"] == "custom_value"

    def test_view_multiple_body_parameters(self) -> None:
        with pytest.raises(RuntimeError) as ex:

            @request_schema(RequestSchema)
            @request_schema(RequestSchema, location="json")
            async def index(request: web.Request, **data: Any) -> web.Response:
                return web.json_response({"msg": "done", "data": {}})

        assert isinstance(ex.value, RuntimeError)
        assert str(ex.value) == "Multiple json locations are not allowed"
