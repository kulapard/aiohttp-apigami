# aiohttp-apigami

![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/kulapard/aiohttp-apigami/ci.yml?branch=master)
[![codecov](https://codecov.io/github/kulapard/aiohttp-apigami/graph/badge.svg?token=Y5EJBF1F25)](https://codecov.io/github/kulapard/aiohttp-apigami)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/kulapard/aiohttp-apigami/master.svg)](https://results.pre-commit.ci/latest/github/kulapard/aiohttp-apigami/master)
[![PyPI - Version](https://img.shields.io/pypi/v/aiohttp-apigami?color=%2334D058&label=pypi%20package)](https://pypi.org/project/aiohttp-apigami)
[![PyPI Downloads](https://static.pepy.tech/badge/aiohttp-apigami)](https://pepy.tech/projects/aiohttp-apigami)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/aiohttp-apigami)
[![GitHub license](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/kulapard/aiohttp-apigami/blob/master/LICENSE)

---

**aiohttp-apigami** brings seamless OpenAPI/Swagger integration and request validation to your [aiohttp](https://github.com/aio-libs/aiohttp) applications using [apispec](https://github.com/marshmallow-code/apispec) and [marshmallow](https://github.com/marshmallow-code/marshmallow).

## 📋 Overview

Think of **aiohttp-apigami** as the bridge between your aiohttp web services and OpenAPI documentation. It solves two key challenges:

1. **Documentation**: Automatically generate interactive OpenAPI/Swagger documentation from your route handlers
2. **Validation**: Enforce request/response schema validation with minimal boilerplate code

### Key Features

- **Decorator-driven API**: Simple `@docs` and `@request_schema` decorators add Swagger/OpenAPI support to your existing code
- **Granular Request Validation**: Specialized decorators for headers, query params, JSON body, etc.
- **Middleware Integration**: Easy validation with `validation_middleware`
- **Built-in Swagger UI**: Ready-to-use interactive documentation (currently <!-- SWAGGER_UI_VERSION_START -->[v5.32.11](https://github.com/swagger-api/swagger-ui/releases/tag/v5.32.11)<!-- SWAGGER_UI_VERSION_END -->)
- **Class-Based View Support**: Fully compatible with aiohttp's CBV pattern
- **Dataclass Support**: Use Python dataclasses directly as schemas for cleaner code
- **Schema Builders**: Pass a callable that builds a `Schema` instance for custom construction

> 💡 **aiohttp-apigami** builds upon the foundation of `aiohttp-apispec` (no longer maintained), with inspiration from the `flask-apispec` library.

## 🚀 Installation

With [uv](https://docs.astral.sh/uv/) package manager:
```bash
uv add aiohttp-apigami
```

Or with pip:
```bash
pip install aiohttp-apigami
```

### Requirements

- Python 3.11+
- aiohttp 3.10+
- apispec 5.0+
- webargs 8.0+
- marshmallow 3.0+
- marshmallow-recipe (optional, required for dataclass support)

## 🧩 Core Components

**aiohttp-apigami** operates on three main building blocks:

1. **Decorators**: Add metadata and validation rules to your handlers
2. **Middleware**: Process requests according to your schemas
3. **Setup Function**: Configure OpenAPI generation and Swagger UI

## 🔍 Quickstart Example

```python
from aiohttp_apigami import (
    docs,
    request_schema,
    response_schema,
    setup_aiohttp_apispec,
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
setup_aiohttp_apispec(
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
from aiohttp_apigami import validation_middleware

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
setup_aiohttp_apispec(
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

## 🔄 Using Dataclasses

Python dataclasses provide a cleaner and more concise way to define request and response schemas:

```python
from dataclasses import dataclass, field
from typing import Any
from aiohttp import web
from aiohttp_apigami import docs, request_schema, response_schema

@dataclass
class NestedData:
    id: int
    name: str

@dataclass
class RequestData:
    id: int
    name: str
    is_active: bool
    tags: list[str]
    nested: NestedData | None = None

@dataclass
class ResponseData:
    message: str
    data: dict[str, Any] = field(default_factory=dict)

@docs(tags=["example"], summary="Dataclass example")
@request_schema(RequestData)  # Use dataclass directly
@response_schema(ResponseData, 200, description="Success")
async def dataclass_handler(request: web.Request):
    # data is an instance of RequestData, not a dictionary
    data: RequestData = request["data"]  # Validated data as a dataclass instance

    return web.json_response({
        "message": "Success",
        "data": {"id": data.id, "name": data.name}  # Access fields as object attributes
    })
```

When using dataclasses with aiohttp-apigami, the validated data is available in the request as actual dataclass instances, not dictionaries. This provides proper type hints and attribute access, improving code readability and IDE support.

Dataclass support requires the `marshmallow-recipe` package. To install it:

```bash
uv add "aiohttp-apigami[dataclass]"
```
or with pip:
```bash
pip install aiohttp-apigami[dataclass]
```

### Generic Dataclasses

You can use generic dataclasses with type parameters to create reusable, type-safe response wrappers:

```python
from dataclasses import dataclass
from typing import Generic, TypeVar
from aiohttp import web
from aiohttp_apigami import docs, response_schema

T = TypeVar('T')

@dataclass
class ApiResponse(Generic[T]):
    success: bool
    message: str
    data: T

# Create type-specific aliases
IntResponse = ApiResponse[int]
UserResponse = ApiResponse[dict]
ListResponse = ApiResponse[list[str]]

@docs(tags=["users"], summary="Get user count")
@response_schema(IntResponse, 200)  # Use the type alias
async def get_count(request: web.Request):
    return web.json_response({
        "success": True,
        "message": "User count retrieved",
        "data": 42
    })

@docs(tags=["users"], summary="Get user details")
@response_schema(UserResponse, 200)  # Different type parameter
async def get_user(request: web.Request):
    return web.json_response({
        "success": True,
        "message": "User retrieved",
        "data": {"id": 1, "name": "John"}
    })

# You can also use generics directly without aliases
@docs(tags=["items"], summary="Get item list")
@response_schema(ApiResponse[list[str]], 200)  # Direct generic usage
async def get_items(request: web.Request):
    return web.json_response({
        "success": True,
        "message": "Items retrieved",
        "data": ["item1", "item2", "item3"]
    })
```

This pattern is particularly useful for:
- **Consistent API responses**: Wrap all responses in a common structure
- **Type safety**: Get proper type checking for response data
- **Code reusability**: Define the wrapper once, use with different data types
- **Better documentation**: Generic types are properly reflected in OpenAPI/Swagger docs

## 🏭 Schema Builders (callable schemas)

Besides a `Schema` class/instance or a dataclass, you can pass any **callable
object that returns a `Schema` instance** when called with no arguments. This
is handy when the schema needs custom construction — for example a
marshmallow-recipe schema with a specific naming case:

```python
import marshmallow as m
import marshmallow_recipe as mr
from dataclasses import dataclass
from aiohttp import web
from aiohttp_apigami import request_schema


@dataclass
class RequestData:
    id: int
    name: str


class SchemaBuilder:
    def __init__(self, data_cls: type) -> None:
        self._data_cls = data_cls

    def __call__(self) -> m.Schema:
        return mr.schema(self._data_cls, naming_case=mr.CAPITAL_CAMEL_CASE)


@request_schema(SchemaBuilder(RequestData))
async def dataclass_handler(request: web.Request):
    data: RequestData = request["data"]
    return web.json_response({"message": "Success", "data": {"id": data.id, "name": data.name}})
```

The builder is invoked once, at decoration time, and the resulting schema is
used for both validation and OpenAPI documentation. A plain `lambda: MySchema()`
works too. The callable must return a `marshmallow.Schema` instance; anything
else raises a `ValueError`.

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

setup_aiohttp_apispec(app, error_callback=my_error_handler)
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
setup_aiohttp_apispec(app, error_callback=my_error_handler)

# Add your middleware BEFORE the validation middleware
app.middlewares.extend([intercept_error, validation_middleware])
```

## ⚠️ Migration from aiohttp-apispec

**aiohttp-apigami** is a near drop-in replacement for `aiohttp-apispec` 2.x. The setup and decorator APIs are compatible (including the `use_kwargs` / `marshal_with` aliases), but the upgrade from webargs < 6 to webargs 8.x changes validation behavior in several ways. Review the items below before migrating — the first group is **silent**: code imports and runs, but requests are validated differently.

### Silent behavior changes

#### 1. The default parse location is now `json` only

With webargs < 6, `@request_schema(MySchema)` without an explicit location searched `querystring`, `form`, and `json` and used whichever had data. aiohttp-apigami parses **only `json`** by default.

If a handler relied on the multi-location fallback (typically GET endpoints reading query parameters through a bare `@request_schema` / `@use_kwargs`), set the location explicitly:

```python
@request_schema(MySchema, location="querystring")
```

#### 2. Unknown request fields now cause 422 errors

webargs < 6 looked up declared schema fields one by one, so extra query parameters or JSON keys were silently ignored. webargs 8 passes the whole payload to the schema, and aiohttp-apigami defers to the schema's `unknown` setting — marshmallow's default is `RAISE`. A request with an unexpected parameter (e.g. `?utm_source=...`) now fails with 422.

To restore the old tolerance, set `unknown` on your schemas (or on a shared base schema):

```python
import marshmallow as ma


class MySchema(ma.Schema):
    class Meta:
        unknown = ma.EXCLUDE
```

#### 3. Multiple schemas without `put_into` no longer merge

`aiohttp-apispec` merged validated data from several `@request_schema` decorators into a single `request["data"]` dict. aiohttp-apigami stores only the **first** schema's data there (and logs a warning). Use `put_into` (or the location shortcuts such as `@querystring_schema`, which set it automatically) to keep each location's data separate:

```python
@request_schema(BodySchema)  # -> request["data"]
@request_schema(QuerySchema, location="querystring", put_into="query")  # -> request["query"]
```

#### 4. Validation error messages are nested by request location

`aiohttp-apispec` relied on webargs < 6, which passed flat field-level messages to the error handler. **aiohttp-apigami** uses webargs 8.x, which nests `ValidationError.messages` under the request location key (`json`, `querystring`, `form`, `headers`, etc.).

**Before (aiohttp-apispec):**

```json
{
  "amount": ["Not a valid number."],
  "reference": ["Missing data for required field."]
}
```

**After (aiohttp-apigami):**

```json
{
  "json": {
    "amount": ["Not a valid number."],
    "reference": ["Missing data for required field."]
  }
}
```

This affects:

- Custom `error_callback` implementations that read `error.messages`
- API clients that parse the default 422 response body

If your API consumers depend on the old flat format, use the built-in `flat_error_handler`, which strips the location level and responds with 422 exactly like `aiohttp-apispec` 2.x:

```python
from aiohttp_apigami import flat_error_handler, setup_aiohttp_apispec

setup_aiohttp_apispec(app, error_callback=flat_error_handler)
```

When validation fails in several locations at once, flattening may overwrite same-named fields — the handler logs an error in that case.

### Loud breaking changes (fail fast)

These surface immediately as exceptions, so they are easy to catch in tests.

#### `locations=[...]` is deprecated — use `location="..."`

The plural `locations` list argument from `aiohttp-apispec` is accepted as a shim: a single-element list works and emits a `DeprecationWarning`. A multi-element list raises `ValueError`, because webargs 8 cannot parse several locations with one schema — split it into one decorator per location:

```python
# Before (aiohttp-apispec)
@request_schema(MySchema, locations=["querystring", "form"])

# After (aiohttp-apigami)
@request_schema(QuerySchema, location="querystring", put_into="query")
@request_schema(FormSchema, location="form", put_into="form")
```

#### Two schemas for the same location raise `RuntimeError`

`aiohttp-apispec` allowed stacking several schemas on one location and merged the results. aiohttp-apigami raises `RuntimeError` at decoration time — combine the fields into a single schema instead.

#### Unknown decorator keyword arguments raise `TypeError`

`@request_schema(MySchema, locatoins=[...])` (note the typo) was silently ignored by `aiohttp-apispec`'s `**kwargs`. aiohttp-apigami raises `TypeError` for any unrecognized keyword argument.

#### Internal app keys were removed

`app["_apispec_parser"]` and `app["_apispec_request_data_name"]` no longer exist (replaced by typed, private `AppKey`s). `app["swagger_dict"]` is still available.

### Other differences

- When no schema targets the default key, `request["data"]` defaults to `{}`, matching `aiohttp-apispec` 2.x (aiohttp-apigami < 0.8 used `[]`).

## 📝 Swagger UI Integration

Enable Swagger UI by adding the `swagger_path` parameter:

```python
setup_aiohttp_apispec(app, swagger_path="/docs")
```

Then navigate to `/docs` in your browser to see the interactive API documentation.

## 🚫 Disabling Spec Generation

You can disable OpenAPI spec generation entirely while keeping request validation working. Useful for tests or production deployments where Swagger UI and the spec endpoint are not needed (skips route scanning, spec building, swagger endpoint, and Swagger UI mounting — saves startup work, especially noticeable with many routes).

Disable via the `generate_spec` parameter:

```python
setup_aiohttp_apispec(
    app=app,
    generate_spec=False,  # skip spec/UI; validation_middleware still works
)
```

Or via the `APIGAMI_GENERATE_SPEC` environment variable (used when `generate_spec` is not passed):

```bash
APIGAMI_GENERATE_SPEC=0 python -m myapp
```

Accepted env values (case-insensitive): `1`/`true`/`yes`/`on` enable, `0`/`false`/`no`/`off` disable. Invalid values fall back to the default (enabled). An explicit `generate_spec=True`/`False` argument always overrides the env var.

When disabled:
- Spec endpoint (`url`) is not registered
- Swagger UI (`swagger_path`) is not mounted
- Route scanning and spec building are skipped
- `validation_middleware` still works — the webargs parser, validated data key, and `error_callback` are still configured

### Testing example

Replaces the `patch("AiohttpApiSpec._register")` workaround for tests that don't need OpenAPI:

```python
import pytest
from aiohttp import web
from aiohttp_apigami import setup_aiohttp_apispec, validation_middleware


@pytest.fixture
def app():
    app = web.Application()
    app.middlewares.append(validation_middleware)
    setup_aiohttp_apispec(app, generate_spec=False)
    return app
```

Or set `APIGAMI_GENERATE_SPEC=0` in your test runner's environment to disable globally without changing app setup.

## 🔄 Updating Swagger UI

This package includes Swagger UI <!-- SWAGGER_UI_VERSION_START -->[v5.32.11](https://github.com/swagger-api/swagger-ui/releases/tag/v5.32.11)<!-- SWAGGER_UI_VERSION_END -->.
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

See [GitHub releases](https://github.com/kulapard/aiohttp-apigami/releases) for version history.

## 💬 Support

If you encounter issues or have suggestions, please [open an issue](https://github.com/kulapard/aiohttp-apigami/issues).

Please ⭐ this repository if it helped you!

## 📜 License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.
