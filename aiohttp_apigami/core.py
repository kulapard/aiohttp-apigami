import enum
import logging.config
from typing import Any

from aiohttp import web
from apispec import APISpec
from apispec.ext.marshmallow import common
from webargs.aiohttpparser import parser

from .constants import APISPEC_PARSER, APISPEC_VALIDATED_DATA_NAME, SWAGGER_DICT
from .plugin import ApigamiPlugin
from .route_processor import RouteProcessor
from .swagger_ui import NAME_SWAGGER_SPEC, LayoutOption, SwaggerUIManager
from .typedefs import SchemaNameResolver, SchemaType

logger = logging.getLogger(__name__)


def resolver(schema: SchemaType) -> str:
    """
    Default schema name resolver.
    Strips 'Schema' from the end of the class name.
    Adds 'Partial-' prefix if schema is a partial schema.
    """
    schema_instance = common.resolve_schema_instance(schema)
    resolved = common.resolve_schema_cls(schema)
    schema_cls = resolved[0] if isinstance(resolved, list) else resolved

    # add prefix to schema name if it is a partial schema
    prefix = "Partial-" if schema_instance.partial else ""
    name = prefix + schema_cls.__name__
    if name.endswith("Schema"):
        # remove "Schema" suffix
        return name[:-6] or name
    return name


class OpenApiVersion(str, enum.Enum):
    V20 = "2.0"
    V300 = "3.0.0"
    V301 = "3.0.1"
    V302 = "3.0.2"
    V303 = "3.0.3"


class AiohttpApiSpec:
    __slots__ = (
        "_registered",
        "_request_data_name",
        "_route_processor",
        "_spec",
        "_swagger_ui",
        "error_callback",
        "prefix",
        "static_path",
        "swagger_path",
        "url",
    )

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
        schema_name_resolver: SchemaNameResolver = resolver,
        openapi_version: str | OpenApiVersion = OpenApiVersion.V20,
        swagger_layout: LayoutOption = LayoutOption.Standalone,
        **options: Any,
    ):
        try:
            openapi_version = OpenApiVersion(openapi_version)
        except ValueError:
            raise ValueError(f"Invalid `openapi_version`: {openapi_version!r}") from None

        # Initialize components
        self._spec = APISpec(
            plugins=(ApigamiPlugin(schema_name_resolver=schema_name_resolver),),
            openapi_version=openapi_version,
            **options,
        )
        self._route_processor = RouteProcessor(self._spec, prefix=prefix)
        self._swagger_ui = SwaggerUIManager(url=url, static_path=static_path, layout=swagger_layout)

        # Store configuration
        self.url = url
        self.swagger_path = swagger_path
        self.static_path = static_path
        self.error_callback = error_callback
        self.prefix = prefix
        self._registered = False
        self._request_data_name = request_data_name

        # Register app if provided
        if app is not None:
            self.register(app, in_place)

    @property
    def spec(self) -> APISpec:
        """Get access to APISpec instance. Deprecated in 1.x release."""
        return self._spec

    def swagger_dict(self) -> dict[str, Any]:
        """Returns swagger spec representation in JSON format"""
        return self._spec.to_dict()

    def register(self, app: web.Application, in_place: bool = False) -> None:
        """Creates spec based on registered app routes and registers needed view"""
        if self._registered is True:
            # Avoid double registration
            logger.warning("API spec is already registered. Skipping registration.")
            return None

        # Set up app configuration
        app[APISPEC_VALIDATED_DATA_NAME] = self._request_data_name
        app[APISPEC_PARSER] = parser

        if self.error_callback:
            parser.error_callback = self.error_callback

        # Register routes and generate API spec
        if in_place:
            self._register(app)
        else:
            self._register_on_startup(app)

        self._registered = True

        # Add Swagger spec endpoint
        if self.url:
            self._setup_spec_endpoint(app, self.url)

            # Set up Swagger UI if path is provided
            if self.swagger_path:
                self._swagger_ui.setup(app, self.swagger_path)

    def _register_on_startup(self, app: web.Application) -> None:
        """Register routes and generate API spec on app startup"""

        async def _async_register(app_: web.Application) -> None:
            self._register(app_)

        app.on_startup.append(_async_register)

    def _register(self, app: web.Application) -> None:
        """Register routes and generate API spec immediately"""
        self._route_processor.register_routes(app)
        app[SWAGGER_DICT] = self.swagger_dict()

    @staticmethod
    def _setup_spec_endpoint(app: web.Application, spec_path: str) -> None:
        async def spec_handler(request: web.Request) -> web.Response:
            return web.json_response(request.app[SWAGGER_DICT])

        spec_path = spec_path if spec_path.startswith("/") else f"/{spec_path}"
        app.router.add_get(spec_path, spec_handler, name=NAME_SWAGGER_SPEC)


def setup_aiohttp_apispec(
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
    schema_name_resolver: SchemaNameResolver = resolver,
    openapi_version: str | OpenApiVersion = OpenApiVersion.V20,
    swagger_layout: LayoutOption = LayoutOption.Standalone,
    **options: Any,
) -> AiohttpApiSpec:
    """
    aiohttp-apigami extension.

    Usage:

    .. code-block:: python

        from aiohttp_apigami import (
            docs,
            request_schema,
            setup_aiohttp_apispec,
        )
        from aiohttp import web
        from marshmallow import Schema, fields


        class RequestSchema(Schema):
            id = fields.Int()
            name = fields.Str(description="name")
            bool_field = fields.Bool()


        @docs(
            tags=["mytag"],
            summary="Test method summary",
            description="Test method description",
        )
        @request_schema(RequestSchema)
        async def index(request):
            return web.json_response({"msg": "done", "data": {}})


        app = web.Application()
        app.router.add_post("/v1/test", index)

        # init docs with all parameters, usual for ApiSpec
        setup_aiohttp_apispec(
            app=app,
            title="My Documentation",
            version="v1",
            url="/api/docs/api-docs",
        )

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
    :param swagger_layout: layout of Swagger UI (``LayoutOption.Standalone`` by default).
                            See ``LayoutOption`` for more details.
    :param options: any apispec.APISpec options
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
        swagger_layout=swagger_layout,
        **options,
    )
