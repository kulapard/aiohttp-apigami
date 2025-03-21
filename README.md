# apispec-aiohttp

![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/kulapard/apispec-aiohttp/ci.yml?branch=master)
[![codecov](https://codecov.io/github/kulapard/apispec-aiohttp/graph/badge.svg?token=Y5EJBF1F25)](https://codecov.io/github/kulapard/apispec-aiohttp)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/kulapard/apispec-aiohttp/master.svg)](https://results.pre-commit.ci/latest/github/kulapard/apispec-aiohttp/master)
[![PyPI - Version](https://img.shields.io/pypi/v/apispec-aiohttp?color=%2334D058&label=pypi%20package)](https://pypi.org/project/apispec-aiohttp)
[![PyPI Downloads](https://static.pepy.tech/badge/apispec-aiohttp)](https://pepy.tech/projects/apispec-aiohttp)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/apispec-aiohttp)
[![GitHub license](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/kulapard/apispec-aiohttp/blob/master/LICENSE)

---

**apispec-aiohttp** brings seamless OpenAPI/Swagger integration and request validation to your [aiohttp](https://github.com/aio-libs/aiohttp) applications using [apispec](https://github.com/marshmallow-code/apispec) and [marshmallow](https://github.com/marshmallow-code/marshmallow).

## 📋 Overview

Think of **apispec-aiohttp** as the bridge between your aiohttp web services and OpenAPI documentation. It solves two key challenges:

1. **Documentation**: Automatically generate interactive OpenAPI/Swagger documentation from your route handlers
2. **Validation**: Enforce request/response schema validation with minimal boilerplate code

### Key Features

- **Decorator-driven API**: Simple `@docs` and `@request_schema` decorators add Swagger/OpenAPI support to your existing code
- **Granular Request Validation**: Specialized decorators for headers, query params, JSON body, etc.
- **Middleware Integration**: Easy validation with `validation_middleware`
- **Built-in Swagger UI**: Ready-to-use interactive documentation (currently <!-- SWAGGER_UI_VERSION_START -->[v5.20.1](https://github.com/swagger-api/swagger-ui/releases/tag/v5.20.1)<!-- SWAGGER_UI_VERSION_END -->)
- **Class-Based View Support**: Fully compatible with aiohttp's CBV pattern

> 💡 **apispec-aiohttp** builds upon the foundation of `aiohttp-apispec` (no longer maintained), with inspiration from the `flask-apispec` library.

## 🚀 Installation

With [uv](https://docs.astral.sh/uv/) package manager:
```bash
uv add apispec-aiohttp
```

Or with pip:
```bash
pip install apispec-aiohttp
```

### Requirements

- Python 3.10+
- aiohttp 3.10+
- apispec 5.0+
- webargs 8.0+
- marshmallow 3.0+

## 🧩 Core Components

**apispec-aiohttp** operates on three main building blocks:

1. **Decorators**: Add metadata and validation rules to your handlers
2. **Middleware**: Process requests according to your schemas
3. **Setup Function**: Configure OpenAPI generation and Swagger UI

## 🔍 Quickstart Example

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

# Initialize documentation with all parameters
setup_apispec_aiohttp(
    app=app,
    title="My Documentation",
    version="v1",
    url="/api/docs/swagger.json",
    swagger_path="/api/docs",
)

# Now you can find:
# - OpenAPI spec at 'http://localhost:8080/api/docs/swagger.json'
# - Swagger UI at 'http://localhost:8080/api/docs'
web.run_app(app)
```

## 🏗️ Usage Patterns

### Class-Based Views

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

### Compact Documentation Style

Document responses directly in the `@docs` decorator for a more compact approach:

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

## ✅ Adding Validation

Enable validation with the middleware:

```python
from apispec_aiohttp import validation_middleware

app.middlewares.append(validation_middleware)
```

Now you can access validated data from `request["data"]`:

```python
@docs(
    tags=["mytag"],
    summary="Test method summary",
    description="Test method description",
)
@request_schema(RequestSchema(strict=True))
async def index(request):
    uid = request["data"]["id"]  # Validated data!
    name = request["data"]["name"]
    return web.json_response(
        {"msg": "done", "data": {"info": f"name - {name}, id - {uid}"}}
    )
```

### Customizing Data Location

You can change the request attribute where validated data is stored:

```python
# Global setting
setup_apispec_aiohttp(
    app=app,
    request_data_name="validated_data",
)

# Or per-view setting
@request_schema(RequestSchema(strict=True), put_into="validated_data")
async def index(request):
    uid = request["validated_data"]["id"]
    # ...
```

## 🎯 Request Part Decorators

For more targeted validation, use these specialized decorators:

| Decorator | Validates | Default Data Location |
|:----------|:----------|:----------------------|
| `match_info_schema` | URL path parameters | `request["match_info"]` |
| `querystring_schema` | URL query parameters | `request["querystring"]` |
| `form_schema` | Form data | `request["form"]` |
| `json_schema` | JSON request body | `request["json"]` |
| `headers_schema` | HTTP headers | `request["headers"]` |
| `cookies_schema` | Cookies | `request["cookies"]` |

### Example:

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
@headers_schema(AuthHeaders)  # Validate headers
@json_schema(UserMeta)  # Validate JSON body
@querystring_schema(UserParams)  # Validate query parameters
async def create_user(request: web.Request):
    headers = request["headers"]  # Validated headers
    json_data = request["json"]  # Validated JSON
    query_params = request["querystring"]  # Validated query parameters
    # ...
```

## 🛡️ Custom Error Handling

Create custom validation error handlers with the `error_callback` parameter:

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

You can also create custom exceptions and handle them in middleware:

```python
class MyException(Exception):
    def __init__(self, message):
        self.message = message

# Can be a coroutine for async operations
async def my_error_handler(
    error, req, schema, error_status_code, error_headers
):
    await req.app["db"].do_smth()  # Async operations
    raise MyException({"errors": error.messages, "text": "Oops"})

# Middleware to handle custom exceptions
@web.middleware
async def intercept_error(request, handler):
    try:
        return await handler(request)
    except MyException as e:
        return web.json_response(e.message, status=400)

# Configure error handler
setup_apispec_aiohttp(app, error_callback=my_error_handler)

# Add your middleware BEFORE the validation middleware
app.middlewares.extend([intercept_error, validation_middleware])
```

## 📝 Swagger UI Integration

Enable Swagger UI by adding the `swagger_path` parameter:

```python
setup_apispec_aiohttp(app, swagger_path="/docs")
```

Then navigate to `/docs` in your browser to see the interactive API documentation.

## 🔄 Updating Swagger UI

This package includes Swagger UI <!-- SWAGGER_UI_VERSION_START -->[v5.20.1](https://github.com/swagger-api/swagger-ui/releases/tag/v5.20.1)<!-- SWAGGER_UI_VERSION_END -->.
Updates are managed through:

1. **Automated Checks**: A weekly GitHub workflow checks for new Swagger UI versions and creates PRs
2. **Manual Updates**: Run `make update-swagger-ui` or `python tools/update_swagger_ui.py`

## 📚 Example Application

A complete example is included in the `example/` directory demonstrating:
- Request/response validation
- Swagger UI integration
- Different schema decorators
- Error handling

To run it:

```bash
make run-example
```

Visit http://localhost:8080 with Swagger UI at http://localhost:8080/api/docs

## 📋 Versioning

This library follows semantic versioning:
- **Major version**: Breaking API changes
- **Minor version**: New backward-compatible features
- **Patch version**: Backward-compatible bug fixes

See [GitHub releases](https://github.com/kulapard/apispec-aiohttp/releases) for version history.

## 💬 Support

If you encounter issues or have suggestions, please [open an issue](https://github.com/kulapard/apispec-aiohttp/issues).

Please ⭐ this repository if it helped you!

## 📜 License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.
