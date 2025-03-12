# apispec-aiohttp

[![Build Status](https://github.com/kulapard/apispec-aiohttp/actions/workflows/ci.yml/badge.svg)](https://github.com/kulapard/apispec-aiohttp/actions/workflows/ci.yml)
[![codecov](https://codecov.io/github/kulapard/apispec-aiohttp/graph/badge.svg?token=Y5EJBF1F25)](https://codecov.io/github/kulapard/apispec-aiohttp)
[![PyPI - Version](https://img.shields.io/pypi/v/apispec-aiohttp?color=%2334D058&label=pypi%20package)](https://pypi.org/project/apispec-aiohttp)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/apispec-aiohttp)
[![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/kulapard/apispec-aiohttp/blob/master/LICENSE)
---

API documentation and validation for [aiohttp](https://github.com/aio-libs/aiohttp) using [apispec](https://github.com/marshmallow-code/apispec)

**apispec-aiohttp** key features:
- `docs` and `request_schema` decorators to add Swagger/OpenAPI spec support out of the box
- Specialized request part decorators: `match_info_schema`, `querystring_schema`, `form_schema`, `json_schema`, `headers_schema` and `cookies_schema` for targeted validation. See [Request Part Decorators](#more-decorators) for details.
- `validation_middleware` middleware to enable validating with marshmallow schemas
- Built-in [Swagger UI](https://github.com/swagger-api/swagger-ui) support

**apispec-aiohttp** API is based on `aiohttp-apispec` (no longer maintained) which was inspired by the `flask-apispec` library


## Contents

- [Install](#install)
- [Example Application](#example-application)
- [Quickstart](#quickstart)
- [Adding validation middleware](#adding-validation-middleware)
- [More decorators](#more-decorators)
- [Custom error handling](#custom-error-handling)
- [SwaggerUI Integration](#swaggerui-integration)


## Install
With [uv](https://docs.astral.sh/uv/) package manager:
```bash
uv add apispec-aiohttp
```
or with pip:
```bash
pip install apispec-aiohttp
```

**Requirements:**
- Python 3.10+
- aiohttp 3.0+
- apispec 5.0+
- webargs 8.0+
- jinja2 3.0+
- marshmallow 3.0+

## Example Application

A fully functional example application is included in the `example/` directory. This example demonstrates all the features of the library including:

- Request and response validation
- Swagger UI integration
- Different schema decorators
- Error handling

To run the example application:

```bash
make run-example
```

The example will be available at http://localhost:8080 with SwaggerUI at http://localhost:8080/api/docs.

## Quickstart

```python
from apispec_aiohttp import (
    docs,
    request_schema,
    response_schema,
    setup_apispec_aiohttp,
)
from aiohttp import web
from marshmallow import Schema, fields


class RequestSchema(Schema):
    id = fields.Int()
    name = fields.Str(description="name")


class ResponseSchema(Schema):
    msg = fields.Str()
    data = fields.Dict()


@docs(
    tags=["mytag"],
    summary="Test method summary",
    description="Test method description",
)
@request_schema(RequestSchema())
@response_schema(ResponseSchema(), 200)
async def index(request):
    # Access validated data from request
    # data = request["data"]
    return web.json_response({"msg": "done", "data": {}})


app = web.Application()
app.router.add_post("/v1/test", index)

# init docs with all parameters, usual for ApiSpec
setup_apispec_aiohttp(
    app=app,
    title="My Documentation",
    version="v1",
    url="/api/docs/swagger.json",
    swagger_path="/api/docs",
)

# Now we can find spec on 'http://localhost:8080/api/docs/swagger.json'
# and docs on 'http://localhost:8080/api/docs'
web.run_app(app)
```

### Class Based Views

Class based views are also supported:
```python
class TheView(web.View):
    @docs(
        tags=["mytag"],
        summary="View method summary",
        description="View method description",
    )
    @request_schema(RequestSchema())
    @response_schema(ResponseSchema(), 200)
    async def delete(self):
        return web.json_response(
            {"msg": "done", "data": {"name": self.request["data"]["name"]}}
        )


app.router.add_view("/v1/view", TheView)
```

### Combining Documentation and Schemas

As an alternative, you can add responses info directly to the `docs` decorator, which is a more compact approach.
This method allows you to document responses without separate decorators:

```python
@docs(
    tags=["mytag"],
    summary="Test method summary",
    description="Test method description",
    responses={
        200: {
            "schema": ResponseSchema,
            "description": "Success response",
        },  # regular response
        404: {"description": "Not found"},  # responses without schema
        422: {"description": "Validation error"},
    },
)
@request_schema(RequestSchema())
async def index(request):
    return web.json_response({"msg": "done", "data": {}})
```

## Adding validation middleware

```Python
from apispec_aiohttp import validation_middleware

...

app.middlewares.append(validation_middleware)
```
Now you can access all validated data in route from ```request['data']``` like so:

```Python
@docs(
    tags=["mytag"],
    summary="Test method summary",
    description="Test method description",
)
@request_schema(RequestSchema(strict=True))
@response_schema(ResponseSchema, 200)
async def index(request):
    uid = request["data"]["id"]
    name = request["data"]["name"]
    return web.json_response(
        {"msg": "done", "data": {"info": f"name - {name}, id - {uid}"}}
    )
```


You can change ``Request``'s ``'data'`` param to another with ``request_data_name`` argument of
``setup_apispec_aiohttp`` function:

```python
setup_apispec_aiohttp(
    app=app,
    request_data_name="validated_data",
)

...


@request_schema(RequestSchema(strict=True))
async def index(request):
    uid = request["validated_data"]["id"]
    ...
```

Also you can do it for specific view using ```put_into```
parameter (beginning from version 2.0):

```python
@request_schema(RequestSchema(strict=True), put_into="validated_data")
async def index(request):
    uid = request["validated_data"]["id"]
    ...
```

## More decorators

You can use specialized decorators for documenting and validating specific parts of a request
such as cookies, headers, and more with these shorthand decorators:

| Decorator name | Default put_into param |
|:----------|:-----------------|
| match_info_schema | match_info |
| querystring_schema | querystring |
| form_schema | form |
| json_schema | json |
| headers_schema | headers |
| cookies_schema | cookies |

### Example Usage of Specialized Schema Decorators:

```python
@docs(
    tags=["users"],
    summary="Create new user",
    description="Add new user to our toy database",
    responses={
        200: {"description": "Ok. User created", "schema": OkResponse},
        401: {"description": "Unauthorized"},
        422: {"description": "Validation error"},
        500: {"description": "Server error"},
    },
)
@headers_schema(AuthHeaders)  # <- schema for headers validation
@json_schema(UserMeta)  # <- schema for json body validation
@querystring_schema(UserParams)  # <- schema for querystring params validation
async def create_user(request: web.Request):
    headers = request["headers"]  # <- validated headers!
    json_data = request["json"]  # <- validated json!
    query_params = request["querystring"]  # <- validated querystring!
    ...
```

## Custom error handling

If you want to catch validation errors by yourself you
could use `error_callback` parameter and create your custom error handler. Note that
it can be one of coroutine or callable and it should
have interface exactly like in examples below:

```python
from marshmallow import ValidationError, Schema
from aiohttp import web
from typing import Optional, Mapping, NoReturn


def my_error_handler(
    error: ValidationError,
    req: web.Request,
    schema: Schema,
    error_status_code: Optional[int] = None,
    error_headers: Optional[Mapping[str, str]] = None,
) -> NoReturn:
    raise web.HTTPBadRequest(
            body=json.dumps(error.messages),
            headers=error_headers,
            content_type="application/json",
        )

setup_apispec_aiohttp(app, error_callback=my_error_handler)
```
Also you can create your own exceptions and create
regular Request in middleware like so:

```python
class MyException(Exception):
    def __init__(self, message):
        self.message = message

# It can be coroutine as well:
async def my_error_handler(
    error, req, schema, error_status_code, error_headers
):
    await req.app["db"].do_smth()  # So you can use some async stuff
    raise MyException({"errors": error.messages, "text": "Oops"})

# This middleware will handle your own exceptions:
@web.middleware
async def intercept_error(request, handler):
    try:
        return await handler(request)
    except MyException as e:
        return web.json_response(e.message, status=400)


setup_apispec_aiohttp(app, error_callback=my_error_handler)

# Do not forget to add your own middleware before validation_middleware
app.middlewares.extend([intercept_error, validation_middleware])
```

## SwaggerUI Integration

Just add `swagger_path` parameter to `setup_apispec_aiohttp` function.

For example:

```python
setup_apispec_aiohttp(app, swagger_path="/docs")
```

Then go to `/docs` to see the SwaggerUI.

## Versioning

This library uses semantic versioning:
- Major version changes indicate breaking API changes
- Minor version changes add new features in a backward-compatible manner
- Patch version changes fix bugs in a backward-compatible manner

Version history is available in the [GitHub releases](https://github.com/kulapard/apispec-aiohttp/releases) page.

## Support

If you encounter any issues or have suggestions for improvements, please open an issue in this GitHub repository.
Please star this repository if this project helped you!

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
