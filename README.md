<h1 align="center">apispec-aiohttp</h1>
<p align="center">Build and document REST APIs with <a href="https://github.com/aio-libs/aiohttp">aiohttp</a> and <a href="https://github.com/marshmallow-code/apispec">apispec</a></p>

<p align="center">
  <a href="https://pypi.python.org/pypi/apispec-aiohttp"><img src="https://badge.fury.io/py/apispec-aiohttp.svg" alt="Pypi"></a>
  <a href="https://github.com/kulapard/apispec-aiohttp/graphs/contributors"><img src="https://img.shields.io/github/contributors/kulapard/apispec-aiohttp.svg" alt="Contributors"></a>
  <a href="https://pepy.tech/project/apispec-aiohttp"><img src="https://pepy.tech/badge/apispec-aiohttp" alt="Downloads"></a>
</p>

<p align="center">
  <a href="https://app.travis-ci.com/github/kulapard/apispec-aiohttp"><img src="https://app.travis-ci.com/kulapard/apispec-aiohttp.svg?branch=master" alt="build status"></a>
  <a href="https://apispec-aiohttp.readthedocs.io/en/latest/?badge=latest"><img src="https://readthedocs.org/projects/apispec-aiohttp/badge/?version=latest" alt="[docs]"></a>
  <a href="https://codecov.io/gh/kulapard/apispec-aiohttp"><img src="https://codecov.io/gh/kulapard/apispec-aiohttp/branch/master/graph/badge.svg" alt="[codcov]"></a>
  <a href="https://github.com/ambv/black"><img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="Code style: black"></a>
</p>

<p>

```apispec-aiohttp``` key features:
- ```docs``` and ```request_schema``` decorators
to add swagger spec support out of the box;
- ```validation_middleware``` middleware to enable validating
with marshmallow schemas from those decorators;
- **SwaggerUI** support.
- *New from version 2.0* -  ```match_info_schema```, ```querystring_schema```,
```form_schema```, ```json_schema```, ```headers_schema``` and ```cookies_schema```
decorators for specific request parts validation.
Look [here](#more-decorators) for more info.

```apispec-aiohttp``` api is based on ```aiohttp-apispec``` (seems abandoned) which is fully inspired by ```flask-apispec``` library


## Contents

- [Install](#install)
- [Quickstart](#quickstart)
- [Adding validation middleware](#adding-validation-middleware)
- [More decorators](#more-decorators)
- [Custom error handling](#custom-error-handling)
- [Build swagger web client](#build-swagger-web-client)
- [Versioning](#versioning)


## Install

```
pip install apispec-aiohttp
```

## Quickstart

```Python
from apispec_aiohttp import (
    docs,
    request_schema,
    setup_apispec_aiohttp,
)
from aiohttp import web
from marshmallow import Schema, fields


class RequestSchema(Schema):
    id = fields.Int()
    name = fields.Str(description="name")


@docs(
    tags=["mytag"],
    summary="Test method summary",
    description="Test method description",
)
@request_schema(RequestSchema(strict=True))
async def index(request):
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
Class based views are also supported:
```python
class TheView(web.View):
    @docs(
        tags=["mytag"],
        summary="View method summary",
        description="View method description",
    )
    @request_schema(RequestSchema(strict=True))
    @response_schema(ResponseSchema(), 200)
    def delete(self):
        return web.json_response(
            {"msg": "done", "data": {"name": self.request["data"]["name"]}}
        )


app.router.add_view("/v1/view", TheView)
```

As alternative you can add responses info to `docs` decorator, which is more compact way.
And it allows you not to use schemas for responses documentation:

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
@request_schema(RequestSchema(strict=True))
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

Starting from version 2.0 you can use shortenings for documenting and validating
specific request parts like cookies, headers etc using those decorators:

| Decorator name | Default put_into param |
|:----------|:-----------------|
| match_info_schema | match_info |
| querystring_schema | querystring |
| form_schema | form |
| json_schema | json |
| headers_schema | headers |
| cookies_schema | cookies |

And example:

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

## Build swagger web client

#### 3.X SwaggerUI version

Just add `swagger_path` parameter to `setup_apispec_aiohttp` function.

For example:

```python
setup_apispec_aiohttp(app, swagger_path="/docs")
```

Then go to `/docs` and see awesome SwaggerUI

#### 2.X SwaggerUI version

If you prefer older version you can use
[aiohttp_swagger](https://github.com/cr0hn/aiohttp-swagger) library.
`apispec-aiohttp` adds `swagger_dict` parameter to aiohttp web application
after initialization (with `setup_apispec_aiohttp` function).
So you can use it easily like:

```Python
from apispec_aiohttp import setup_apispec_aiohttp
from aiohttp_swagger import setup_swagger


def create_app(app):
    setup_apispec_aiohttp(app)

    async def swagger(app):
        setup_swagger(
            app=app, swagger_url="/api/doc", swagger_info=app["swagger_dict"]
        )

    app.on_startup.append(swagger)
    # now we can access swagger client on '/api/doc' url
    ...
    return app
```

## Versioning

This software follows [Semantic Versioning](http://semver.org/).

------

Please star this repository if this project helped you!
