from typing import Any

import pytest

pytestmark = pytest.mark.asyncio


async def test_response_200_get(aiohttp_app: Any) -> None:
    res = await aiohttp_app.get("/v1/test", params={"id": 1, "name": "max"})
    assert res.status == 200


async def test_response_400_get(aiohttp_app: Any) -> None:
    res = await aiohttp_app.get("/v1/test", params={"id": "string", "name": "max"})
    assert res.status == 400
    assert await res.json() == {
        "errors": {"querystring": {"id": ["Not a valid integer."]}},
        "text": "Oops",
    }


async def test_response_200_post(aiohttp_app: Any) -> None:
    res = await aiohttp_app.post("/v1/test", json={"id": 1, "name": "max"})
    assert res.status == 200


async def test_response_200_post_callable_schema(aiohttp_app: Any) -> None:
    res = await aiohttp_app.post("/v1/test_call", json={"id": 1, "name": "max"})
    assert res.status == 200


async def test_response_400_post(aiohttp_app: Any) -> None:
    res = await aiohttp_app.post("/v1/test", json={"id": "string", "name": "max"})
    assert res.status == 400
    assert await res.json() == {
        "errors": {"json": {"id": ["Not a valid integer."]}},
        "text": "Oops",
    }


async def test_response_400_post_unknown_toplevel_field(aiohttp_app: Any) -> None:
    # unknown_field is not a field in RequestSchema, default behavior is RAISE exception
    res = await aiohttp_app.post("/v1/test", json={"id": 1, "name": "max", "unknown_field": "string"})
    assert res.status == 400
    assert await res.json() == {
        "errors": {"json": {"unknown_field": ["Unknown field."]}},
        "text": "Oops",
    }


async def test_response_400_post_nested_fields(aiohttp_app: Any) -> None:
    payload = {
        "nested_field": {
            "i": 12,
            "j": 12,  # unknown nested field
        }
    }
    res = await aiohttp_app.post("/v1/test", json=payload)
    assert res.status == 400
    assert await res.json() == {
        "errors": {"json": {"nested_field": {"j": ["Unknown field."]}}},
        "text": "Oops",
    }


async def test_response_not_docked(aiohttp_app: Any) -> None:
    res = await aiohttp_app.get("/v1/other", params={"id": 1, "name": "max"})
    assert res.status == 200


async def test_response_data_post(aiohttp_app: Any) -> None:
    res = await aiohttp_app.post("/v1/echo", json={"id": 1, "name": "max", "list_field": [1, 2, 3, 4]})
    assert (await res.json()) == {"id": 1, "name": "max", "list_field": [1, 2, 3, 4]}


async def test_response_data_get(aiohttp_app: Any) -> None:
    res = await aiohttp_app.get(
        "/v1/echo",
        params=[
            ("id", "1"),
            ("name", "max"),
            ("bool_field", "0"),
            ("list_field", "1"),
            ("list_field", "2"),
            ("list_field", "3"),
            ("list_field", "4"),
        ],
    )
    assert (await res.json()) == {
        "id": 1,
        "name": "max",
        "bool_field": False,
        "list_field": [1, 2, 3, 4],
    }


async def test_response_data_class_get(aiohttp_app: Any) -> None:
    res = await aiohttp_app.get(
        "/v1/class_echo",
        params=[
            ("id", "1"),
            ("name", "max"),
            ("bool_field", "0"),
            ("list_field", "1"),
            ("list_field", "2"),
            ("list_field", "3"),
            ("list_field", "4"),
        ],
    )
    assert (await res.json()) == {
        "id": 1,
        "name": "max",
        "bool_field": False,
        "list_field": [1, 2, 3, 4],
    }


async def test_response_data_class_post(aiohttp_app: Any) -> None:
    res = await aiohttp_app.post("/v1/class_echo")
    assert res.status == 405


async def test_path_variable_described_correctly(aiohttp_app: Any) -> None:
    if aiohttp_app.app._subapps:
        swag = aiohttp_app.app._subapps[0]["swagger_dict"]["paths"]["/v1/variable/{var}"]
    else:
        swag = aiohttp_app.app["swagger_dict"]["paths"]["/v1/variable/{var}"]
    assert len(swag["get"]["parameters"]) == 1, "There should only be one"
    assert swag["get"]["parameters"][0]["name"] == "var"
    assert swag["get"]["parameters"][0]["schema"]["format"] == "uuid"


async def test_response_data_class_without_spec(aiohttp_app: Any) -> None:
    res = await aiohttp_app.delete("/v1/class_echo")
    assert (await res.json()) == {"hello": "world"}


async def test_swagger_handler_200(aiohttp_app: Any) -> None:
    res = await aiohttp_app.get("/v1/api/docs/api-docs")
    assert res.status == 200


async def test_match_info(aiohttp_app: Any) -> None:
    res = await aiohttp_app.get("/v1/variable/hello")
    assert res.status == 200
    assert await res.json() == []


async def test_validators(aiohttp_app: Any) -> None:
    res = await aiohttp_app.post(
        "/v1/validate/123456",
        json={"id": 1, "name": "max", "bool_field": False, "list_field": [1, 2, 3, 4]},
        params=[
            ("id", "1"),
            ("name", "max"),
            ("bool_field", "0"),
            ("list_field", "1"),
            ("list_field", "2"),
            ("list_field", "3"),
            ("list_field", "4"),
        ],
        cookies={"some_cookie": "test-cookie-value"},
        headers={"some_header": "test-header-value"},
    )
    assert res.status == 200
    assert await res.json() == {
        "json": {
            "id": 1,
            "name": "max",
            "bool_field": False,
            "list_field": [1, 2, 3, 4],
        },
        "querystring": {
            "id": 1,
            "name": "max",
            "bool_field": False,
            "list_field": [1, 2, 3, 4],
        },
        "cookies": {"some_cookie": "test-cookie-value"},
        "headers": {"some_header": "test-header-value"},
        "match_info": {"uuid": 123456},
    }


async def test_swagger_path(aiohttp_app: Any) -> None:
    res = await aiohttp_app.get("/v1/api/docs")
    assert res.status == 200


async def test_swagger_static(aiohttp_app: Any) -> None:
    assert (await aiohttp_app.get("/static/swagger/swagger-ui.css")).status == 200 or (
        await aiohttp_app.get("/v1/static/swagger/swagger-ui.css")
    ).status == 200


async def test_dataclass_success(aiohttp_app: Any, example_for_request_dataclass: dict[str, Any]) -> None:
    """Test successful request with dataclass handler."""
    res = await aiohttp_app.post("/v1/dataclass", json=example_for_request_dataclass)
    assert res.status == 200
    json_data = await res.json()
    assert json_data["msg"] == "done"
    assert json_data["data"]["id"] == example_for_request_dataclass["id"]
    assert json_data["data"]["name"] == example_for_request_dataclass["name"]
    assert json_data["data"]["is_active"] == example_for_request_dataclass["bool_field"]


async def test_dataclass_validation_error(aiohttp_app: Any) -> None:
    """Test validation error with dataclass handler."""
    # Missing required fields
    res = await aiohttp_app.post("/v1/dataclass", json={"id": "not_an_int"})
    assert res.status == 400
    error_data = await res.json()
    assert "errors" in error_data

    # Test with invalid data type
    invalid_data = {
        "id": "not_an_integer",  # should be int
        "name": 123,  # should be string
        "bool_field": "not_a_boolean",  # should be boolean
        "list_field": "not_a_list",  # should be list
    }
    res = await aiohttp_app.post("/v1/dataclass", json=invalid_data)
    assert res.status == 400
    error_data = await res.json()
    assert "errors" in error_data


async def test_dataclass_in_swagger_docs(aiohttp_app: Any) -> None:
    """Test that dataclass endpoint is correctly documented in Swagger."""
    # Get the Swagger JSON
    res = await aiohttp_app.get("/v1/api/docs/api-docs")
    assert res.status == 200
    swagger_json = await res.json()

    # Verify that the dataclass endpoint and schema exist somewhere in the swagger docs
    paths = swagger_json["paths"]
    dataclass_path = None

    # Find the dataclass endpoint in the swagger docs
    for path, methods in paths.items():
        if "post" in methods and "tags" in methods["post"] and "dataclass" in methods["post"]["tags"]:
            dataclass_path = path
            break

    assert dataclass_path is not None, "Dataclass endpoint not found in Swagger docs"

    # Get the post spec for the dataclass endpoint
    post_spec = paths[dataclass_path]["post"]

    # Verify tags and summary
    assert "dataclass" in post_spec["tags"]
    assert post_spec["summary"] == "Test dataclass handler"

    # Verify request schema exists (Swagger 2.0 format)
    assert "parameters" in post_spec
    body_param = None
    for param in post_spec["parameters"]:
        if param["in"] == "body":
            body_param = param
            break
    assert body_param is not None, "No body parameter found in Swagger docs"
    assert "schema" in body_param
    assert "$ref" in body_param["schema"]
    assert "RequestDataclass" in body_param["schema"]["$ref"]

    # Verify response schema exists
    assert "responses" in post_spec
    assert "200" in post_spec["responses"]
    assert post_spec["responses"]["200"]["description"] == "Success response with dataclass"
    assert "schema" in post_spec["responses"]["200"]
    assert "$ref" in post_spec["responses"]["200"]["schema"]
    assert "ResponseDataclass" in post_spec["responses"]["200"]["schema"]["$ref"]

    # Also verify that the definitions include our dataclass schemas
    assert "definitions" in swagger_json
    assert "RequestDataclass" in swagger_json["definitions"]
    assert "ResponseDataclass" in swagger_json["definitions"]
