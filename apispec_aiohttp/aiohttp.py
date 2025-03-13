import copy
import enum
import json
import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from string import Template
from typing import Any

import marshmallow as ma
from aiohttp import web
from aiohttp.hdrs import METH_ALL, METH_ANY
from aiohttp.helpers import AppKey
from apispec import APISpec
from apispec.core import VALID_METHODS_OPENAPI_V2
from apispec.ext.marshmallow import MarshmallowPlugin, common
from webargs.aiohttpparser import AIOHTTPParser, parser

from .utils import get_path, get_path_keys, issubclass_py37fix

_AiohttpView = Callable[[web.Request], Awaitable[web.StreamResponse]]
_SchemaType = type[ma.Schema] | ma.Schema | str
_SchemaNameResolver = Callable[[type[ma.Schema]], str]

VALID_RESPONSE_FIELDS = {"description", "headers", "examples"}

DEFAULT_RESPONSE_LOCATION = "json"

NAME_SWAGGER_SPEC = "swagger.spec"
NAME_SWAGGER_DOCS = "swagger.docs"
NAME_SWAGGER_STATIC = "swagger.static"

SWAGGER_UI_STATIC_FILES = Path(__file__).parent / "swagger_ui"
INDEX_PAGE = "index.html"

APISPEC_VALIDATED_DATA_NAME = AppKey("_apispec_validated_data_name", str)
APISPEC_PARSER = AppKey("_apispec_parser", AIOHTTPParser)

# TODO: make it AppKey in 1.x release
# Leave as a string for backward compatibility with 0.x
SWAGGER_DICT = "swagger_dict"


@dataclass
class HandlerSchema:
    schema: ma.Schema
    location: str
    put_into: str | None = None


def resolver(schema: _SchemaType) -> str:
    schema_instance = common.resolve_schema_instance(schema)
    prefix = "Partial-" if schema_instance.partial else ""
    schema_cls = common.resolve_schema_cls(schema)
    name = prefix + schema_cls.__name__ if hasattr(schema_cls, "__name__") else "Schema"
    if name.endswith("Schema"):
        return name[:-6] or name
    return name


class OpenApiVersion(str, enum.Enum):
    V20 = "2.0"
    V300 = "3.0.0"
    V301 = "3.0.1"
    V302 = "3.0.2"
    V303 = "3.0.3"


class AiohttpApiSpec:
    def __init__(
        self,
        url: str = "/api/docs/swagger.json",
        app: web.Application | None = None,
        request_data_name: str = "data",
        swagger_path: str | None = None,
        static_path: str = "/static/swagger",
        error_callback: Any = None,
        in_place: bool = False,
        prefix: str = "",
        schema_name_resolver: _SchemaNameResolver = resolver,
        openapi_version: str | OpenApiVersion | None = None,
        **kwargs: Any,
    ):
        openapi_version = openapi_version or OpenApiVersion.V20
        try:
            openapi_version = OpenApiVersion(openapi_version)
        except ValueError:
            raise ValueError(f"Invalid `openapi_version`: {openapi_version!r}") from None

        self.plugin = MarshmallowPlugin(schema_name_resolver=schema_name_resolver)
        self.spec = APISpec(
            plugins=(self.plugin,),
            openapi_version=openapi_version.value,
            **kwargs,
        )

        self.url = url
        self.swagger_path = swagger_path
        self.static_path = static_path
        self._registered = False
        self._request_data_name = request_data_name
        self.error_callback = error_callback
        self.prefix = prefix
        self._index_page: str | None = None
        if app is not None:
            self.register(app, in_place)

    def swagger_dict(self) -> dict[str, Any]:
        """Returns swagger spec representation in JSON format"""
        return self.spec.to_dict()

    def register(self, app: web.Application, in_place: bool = False) -> None:
        """Creates spec based on registered app routes and registers needed view"""
        if self._registered is True:
            return None

        app[APISPEC_VALIDATED_DATA_NAME] = self._request_data_name

        if self.error_callback:
            parser.error_callback = self.error_callback
        app[APISPEC_PARSER] = parser

        if in_place:
            self._register(app)
        else:

            async def doc_routes(app_: web.Application) -> None:
                self._register(app_)

            app.on_startup.append(doc_routes)

        self._registered = True

        if self.url is not None:

            async def swagger_handler(request: web.Request) -> web.Response:
                return web.json_response(request.app[SWAGGER_DICT])

            route_url = self.url
            if not self.url.startswith("/"):
                route_url = f"/{self.url}"
            app.router.add_route("GET", route_url, swagger_handler, name=NAME_SWAGGER_SPEC)

            if self.swagger_path is not None:
                self._add_swagger_web_page(app, self.static_path, self.swagger_path)

    def _get_index_page(self, app: web.Application | None, static_files: Path, static_path: str) -> str:
        if self._index_page is not None:
            return self._index_page

        with open(str(static_files / INDEX_PAGE)) as swg_tmp:
            url = self.url if app is None else str(app.router[NAME_SWAGGER_SPEC].url_for())

            if app is not None:
                static_url = app.router[NAME_SWAGGER_STATIC].url_for(filename=INDEX_PAGE)
                static_path = os.path.dirname(str(static_url))

            if not self.spec.options.get("display_configurations"):
                self.spec.options["display_configurations"] = {}

            self._index_page = Template(swg_tmp.read()).substitute(
                path=url,
                static=static_path,
                display_configurations=json.dumps(self.spec.options["display_configurations"]),
            )

        assert self._index_page is not None  # for mypy
        return self._index_page

    def _add_swagger_web_page(self, app: web.Application, static_path: str, view_path: str) -> None:
        app.router.add_static(static_path, SWAGGER_UI_STATIC_FILES, name=NAME_SWAGGER_STATIC)

        async def swagger_view(_: web.Request) -> web.Response:
            index_page = self._get_index_page(app, SWAGGER_UI_STATIC_FILES, static_path)
            return web.Response(text=index_page, content_type="text/html")

        app.router.add_route("GET", view_path, swagger_view, name=NAME_SWAGGER_DOCS)

    def _register(self, app: web.Application) -> None:
        for route in app.router.routes():
            if issubclass_py37fix(route.handler, web.View) and route.method == METH_ANY:
                for attr in dir(route.handler):
                    if attr.upper() in METH_ALL:
                        view = getattr(route.handler, attr)
                        method = attr
                        self._register_route(route, method, view)
            else:
                method = route.method.lower()
                view = route.handler
                self._register_route(route, method, view)
        app[SWAGGER_DICT] = self.swagger_dict()

    def _register_route(self, route: web.AbstractRoute, method: str, view: _AiohttpView) -> None:
        if not hasattr(view, "__apispec__"):
            return None

        url_path = get_path(route)
        if not url_path:
            return None

        self._update_paths(view.__apispec__, method, self.prefix + url_path)

    def _update_paths(self, data: dict[str, Any], method: str, url_path: str) -> None:
        if method not in VALID_METHODS_OPENAPI_V2:
            return None
        for schema in data.pop("schemas", []):
            parameters = self.plugin.converter.schema2parameters(  # type: ignore[union-attr]
                schema["schema"], location=schema["location"], **schema["options"]
            )
            self._add_examples(schema["schema"], parameters, schema["example"])
            data["parameters"].extend(parameters)

        existing = [p["name"] for p in data["parameters"] if p["in"] == "path"]
        data["parameters"].extend(
            {"in": "path", "name": path_key, "required": True, "type": "string"}
            for path_key in get_path_keys(url_path)
            if path_key not in existing
        )

        if "responses" in data:
            responses = {}
            for code, actual_params in data["responses"].items():
                if "schema" in actual_params:
                    raw_parameters = self.plugin.converter.schema2parameters(  # type: ignore[union-attr]
                        actual_params["schema"],
                        location=DEFAULT_RESPONSE_LOCATION,
                        required=actual_params.get("required", False),
                    )[0]
                    updated_params = {k: v for k, v in raw_parameters.items() if k in VALID_RESPONSE_FIELDS}
                    if self.spec.components.openapi_version.major < 3:
                        updated_params["schema"] = actual_params["schema"]
                    else:
                        updated_params["content"] = {
                            "application/json": {
                                "schema": actual_params["schema"],
                            },
                        }
                    for extra_info in ("description", "headers", "examples"):
                        if extra_info in actual_params:
                            updated_params[extra_info] = actual_params[extra_info]
                    responses[code] = updated_params
                else:
                    responses[code] = actual_params
            data["responses"] = responses

        operations = copy.deepcopy(data)
        self.spec.path(path=url_path, operations={method: operations})

    def _add_examples(
        self, ref_schema: _SchemaType, endpoint_schema: list[dict[str, Any]], example: dict[str, Any] | None
    ) -> None:
        def add_to_endpoint_or_ref() -> None:
            if add_to_refs and name is not None:
                self.spec.components.schemas[name]["example"] = example
            else:
                # Get the reference path from $ref field
                ref_path = endpoint_schema[0]["schema"].pop("$ref")
                # Ensure there's no duplication of #/definitions/
                if "#/definitions/#/definitions/" in ref_path:
                    ref_path = ref_path.replace("#/definitions/#/definitions/", "#/definitions/")
                endpoint_schema[0]["schema"]["allOf"] = [{"$ref": ref_path}]
                endpoint_schema[0]["schema"]["example"] = example

        if not example:
            return
        schema_instance = common.resolve_schema_instance(ref_schema)
        name = self.plugin.converter.schema_name_resolver(schema_instance)  # type: ignore[union-attr]
        add_to_refs = example.pop("add_to_refs", False)  # Default to False if key doesn't exist
        if self.spec.components.openapi_version.major < 3:
            if name and name in self.spec.components.schemas:
                add_to_endpoint_or_ref()
        else:
            add_to_endpoint_or_ref()


def setup_apispec_aiohttp(
    app: web.Application,
    *,
    title: str = "API documentation",
    version: str = "0.0.1",
    url: str = "/api/docs/swagger.json",
    request_data_name: str = "data",
    swagger_path: str | None = None,
    static_path: str = "/static/swagger",
    error_callback: Any = None,
    in_place: bool = False,
    prefix: str = "",
    schema_name_resolver: _SchemaNameResolver = resolver,
    openapi_version: str | OpenApiVersion = OpenApiVersion.V20,
    **kwargs: Any,
) -> AiohttpApiSpec:
    """
    apispec-aiohttp extension.

    Usage:

    .. code-block:: python

        from apispec_aiohttp import docs, request_schema, setup_apispec_aiohttp
        from aiohttp import web
        from marshmallow import Schema, fields


        class RequestSchema(Schema):
            id = fields.Int()
            name = fields.Str(description='name')
            bool_field = fields.Bool()


        @docs(tags=['mytag'],
              summary='Test method summary',
              description='Test method description')
        @request_schema(RequestSchema)
        async def index(request):
            return web.json_response({'msg': 'done', 'data': {}})


        app = web.Application()
        app.router.add_post('/v1/test', index)

        # init docs with all parameters, usual for ApiSpec
        setup_apispec_aiohttp(app=app,
                              title='My Documentation',
                              version='v1',
                              url='/api/docs/api-docs')

        # now we can find it on 'http://localhost:8080/api/docs/api-docs'
        web.run_app(app)

    :param Application app: aiohttp web app
    :param str title: API title
    :param str version: API version
    :param str url: url for swagger spec in JSON format
    :param str request_data_name: name of the key in Request object
                                  where validated data will be placed by
                                  validation_middleware (``'data'`` by default)
    :param str swagger_path: experimental SwaggerUI support (starting from v1.1.0).
                             By default it is None (disabled)
    :param str static_path: path for static files used by SwaggerUI
                            (if it is enabled with ``swagger_path``)
    :param error_callback: custom error handler
    :param in_place: register all routes at the moment of calling this function
                     instead of the moment of the on_startup signal.
                     If True, be sure all routes are added to router
    :param prefix: prefix to add to all registered routes
    :param schema_name_resolver: custom schema_name_resolver for MarshmallowPlugin.
    :param openapi_version: version of OpenAPI schema
    :param kwargs: any apispec.APISpec kwargs
    :return: return instance of AiohttpApiSpec class
    :rtype: AiohttpApiSpec
    """
    return AiohttpApiSpec(
        url,
        app,
        request_data_name,
        title=title,
        version=version,
        swagger_path=swagger_path,
        static_path=static_path,
        error_callback=error_callback,
        in_place=in_place,
        prefix=prefix,
        schema_name_resolver=schema_name_resolver,
        openapi_version=openapi_version,
        **kwargs,
    )
