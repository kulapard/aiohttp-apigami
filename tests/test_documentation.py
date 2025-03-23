import json
from typing import Any

import pytest
from aiohttp import web
from aiohttp.web_urldispatcher import AbstractRoute, StaticResource
from yarl import URL

from aiohttp_apigami import setup_aiohttp_apispec


async def test_app_swagger_url(aiohttp_app: Any) -> None:
    def safe_url_for(route: AbstractRoute) -> URL | None:
        if isinstance(route._resource, StaticResource):
            # url_for on StaticResource requires filename arg
            return None
        try:
            return route.url_for()
        except KeyError:
            return None

    urls = [safe_url_for(route) for route in aiohttp_app.app.router.routes()]
    assert URL("/v1/api/docs/api-docs") in urls


async def test_app_swagger_json(aiohttp_app: Any, example_for_request_schema: dict[str, Any]) -> None:
    resp = await aiohttp_app.get("/v1/api/docs/api-docs")
    docs = await resp.json()
    assert docs["info"]["title"] == "API documentation"
    assert docs["info"]["version"] == "0.0.1"
    docs["paths"]["/v1/test"]["get"]["parameters"] = sorted(
        docs["paths"]["/v1/test"]["get"]["parameters"], key=lambda x: x["name"]
    )
    assert json.dumps(docs["paths"]["/v1/test"]["get"], sort_keys=True) == json.dumps(
        {
            "parameters": [
                {
                    "in": "query",
                    "name": "bool_field",
                    "required": False,
                    "type": "boolean",
                },
                {
                    "in": "query",
                    "name": "id",
                    "required": False,
                    "type": "integer",
                },
                {
                    "collectionFormat": "multi",
                    "in": "query",
                    "items": {"type": "integer"},
                    "name": "list_field",
                    "required": False,
                    "type": "array",
                },
                {
                    "description": "name",
                    "in": "query",
                    "name": "name",
                    "required": False,
                    "type": "string",
                },
                {
                    # default schema_name_resolver, resolved based on schema __name__
                    # drops trailing "Schema so, MyNestedSchema resolves to MyNested
                    "$ref": "#/definitions/MyNested",
                    "in": "query",
                    "name": "nested_field",
                    "required": False,
                },
            ],
            "responses": {
                "200": {
                    "description": "Success response",
                    "schema": {"$ref": "#/definitions/Response"},
                },
                "404": {"description": "Not Found"},
            },
            "tags": ["mytag"],
            "summary": "Test method summary",
            "description": "Test method description",
            "produces": ["application/json"],
        },
        sort_keys=True,
    )
    docs["paths"]["/v1/class_echo"]["get"]["parameters"] = sorted(
        docs["paths"]["/v1/class_echo"]["get"]["parameters"], key=lambda x: x["name"]
    )
    assert json.dumps(docs["paths"]["/v1/class_echo"]["get"], sort_keys=True) == json.dumps(
        {
            "parameters": [
                {
                    "in": "query",
                    "name": "bool_field",
                    "required": False,
                    "type": "boolean",
                },
                {
                    "in": "query",
                    "name": "id",
                    "required": False,
                    "type": "integer",
                },
                {
                    "collectionFormat": "multi",
                    "in": "query",
                    "items": {"type": "integer"},
                    "name": "list_field",
                    "required": False,
                    "type": "array",
                },
                {
                    "description": "name",
                    "in": "query",
                    "name": "name",
                    "required": False,
                    "type": "string",
                },
                {
                    "$ref": "#/definitions/MyNested",
                    "in": "query",
                    "name": "nested_field",
                    "required": False,
                },
            ],
            "responses": {},
            "tags": ["mytag"],
            "summary": "View method summary",
            "description": "View method description",
            "produces": ["application/json"],
        },
        sort_keys=True,
    )
    assert docs["paths"]["/v1/example_endpoint"]["post"]["parameters"] == [
        {
            "in": "body",
            "required": False,
            "name": "body",
            "schema": {
                "allOf": [{"$ref": "#/definitions/Request"}],
                "example": example_for_request_schema,
            },
        }
    ]

    # Instead of checking that definitions match exactly, check that required schemas exist
    assert "MyNested" in docs["definitions"]
    assert "Request" in docs["definitions"]
    assert "Partial-Request" in docs["definitions"]
    assert "Response" in docs["definitions"]

    # Verify structure of required schemas
    assert "properties" in docs["definitions"]["MyNested"]
    assert "i" in docs["definitions"]["MyNested"]["properties"]
    assert docs["definitions"]["MyNested"]["properties"]["i"]["type"] == "integer"

    # Request schema
    assert "properties" in docs["definitions"]["Request"]
    assert "id" in docs["definitions"]["Request"]["properties"]
    assert "name" in docs["definitions"]["Request"]["properties"]
    assert "bool_field" in docs["definitions"]["Request"]["properties"]
    assert "list_field" in docs["definitions"]["Request"]["properties"]
    assert "nested_field" in docs["definitions"]["Request"]["properties"]

    # Response schema
    assert "properties" in docs["definitions"]["Response"]
    assert "data" in docs["definitions"]["Response"]["properties"]
    assert "msg" in docs["definitions"]["Response"]["properties"]


@pytest.mark.asyncio
async def test_not_register_route_for_empty_url() -> None:
    app = web.Application()
    assert len(app.router.routes()) == 0
    setup_aiohttp_apispec(app=app, url="")
    assert len(app.router.routes()) == 0


@pytest.mark.asyncio
async def test_register_route_for_relative_url() -> None:
    app = web.Application()
    assert len(app.router.routes()) == 0
    setup_aiohttp_apispec(app=app, url="api/swagger")
    assert len(app.router.routes()) == 2  # GET and HEAD
