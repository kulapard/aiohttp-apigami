import copy
from typing import Any

from aiohttp import web
from aiohttp.hdrs import METH_ALL, METH_ANY
from apispec.core import VALID_METHODS_OPENAPI_V2
from apispec.ext.marshmallow import common

from .constants import API_SPEC_ATTR
from .spec import SpecManager
from .typedefs import HandlerType, SchemaType
from .utils import get_path, get_path_keys, is_class_based_view

VALID_RESPONSE_FIELDS = {"description", "headers", "examples"}
DEFAULT_RESPONSE_LOCATION = "json"


class RouteProcessor:
    """Processes aiohttp routes to extract OpenAPI data."""

    __slots__ = ("_prefix", "_spec_manager")

    def __init__(self, spec_manager: SpecManager, prefix: str = ""):
        self._spec_manager = spec_manager
        self._prefix = prefix

    def schema2parameters(self, *, schema: SchemaType, location: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Convert a schema to OpenAPI parameters."""
        return self._spec_manager.schema2parameters(schema, location=location, **kwargs)

    def add_example(
        self, *, schema: SchemaType, parameters: list[dict[str, Any]], example: dict[str, Any] | None
    ) -> None:
        """Add examples to schema or endpoint."""
        if not example:
            return

        schema_instance = common.resolve_schema_instance(schema)
        schema_name = self._spec_manager.get_schema_name(schema_instance)
        add_to_refs = example.pop("add_to_refs", False)  # Default to False if key doesn't exist

        def _add_to_endpoint_or_ref() -> None:
            if add_to_refs and schema_name is not None:
                self._spec_manager.schemas[schema_name]["example"] = example
            else:
                # Get the reference path from $ref field
                ref_path = parameters[0]["schema"].pop("$ref")
                # Ensure there's no duplication of #/definitions/
                if "#/definitions/#/definitions/" in ref_path:
                    ref_path = ref_path.replace("#/definitions/#/definitions/", "#/definitions/")
                parameters[0]["schema"]["allOf"] = [{"$ref": ref_path}]
                parameters[0]["schema"]["example"] = example

        if self._spec_manager.openapi_version.major < 3:
            if schema_name and schema_name in self._spec_manager.schemas:
                _add_to_endpoint_or_ref()
        else:
            _add_to_endpoint_or_ref()

    def register_routes(self, app: web.Application) -> None:
        """Register all routes from the application."""
        for route in app.router.routes():
            # Class based views have multiple methods
            # Register each method separately
            if is_class_based_view(route.handler) and route.method == METH_ANY:
                for attr in dir(route.handler):
                    if attr.upper() in METH_ALL:
                        method = attr
                        sub_handler = getattr(route.handler, attr)
                        self.register_route(route=route, method=method, handler=sub_handler)

            # Function based views have a single method
            else:
                method = route.method.lower()
                handler = route.handler
                self.register_route(route=route, method=method, handler=handler)

    def register_route(self, *, route: web.AbstractRoute, method: str, handler: HandlerType) -> None:
        """Register a single route."""
        if not hasattr(handler, API_SPEC_ATTR):
            return None

        url_path = get_path(route)
        if not url_path:
            return None

        handle_apispec = getattr(handler, API_SPEC_ATTR, {})
        self.update_paths(path=self._prefix + url_path, method=method, handler_apispec=handle_apispec)

    def update_paths(self, *, path: str, method: str, handler_apispec: dict[str, Any]) -> None:
        """Update spec paths with route information."""
        if method not in VALID_METHODS_OPENAPI_V2:
            return None

        for schema in handler_apispec.pop("schemas", []):
            schema_instance = schema["schema"]
            parameters = self.schema2parameters(
                schema=schema_instance, location=schema["location"], **schema["options"]
            )
            self.add_example(schema=schema_instance, parameters=parameters, example=schema["example"])
            handler_apispec["parameters"].extend(parameters)

        # Update path keys if they are not already present in the handler_apispec
        existing_path_keys = {p["name"] for p in handler_apispec["parameters"] if p["in"] == "path"}
        new_path_keys = (path_key for path_key in get_path_keys(path) if path_key not in existing_path_keys)
        new_path_keys_params = [
            {"in": "path", "name": path_key, "required": True, "type": "string"} for path_key in new_path_keys
        ]
        handler_apispec["parameters"].extend(new_path_keys_params)

        #
        if "responses" in handler_apispec:
            handler_apispec["responses"] = self._process_responses(handler_apispec["responses"])

        handler_apispec = copy.deepcopy(handler_apispec)
        self._spec_manager.app_path(path=path, method=method, handler_apispec=handler_apispec)

    def _process_responses(self, responses_data: dict[str, Any]) -> dict[str, Any]:
        """Process response schemas for the spec."""
        responses = {}
        for code, actual_params in responses_data.items():
            if "schema" in actual_params:
                raw_parameters = self.schema2parameters(
                    schema=actual_params["schema"],
                    location=DEFAULT_RESPONSE_LOCATION,
                    required=actual_params.get("required", False),
                )[0]
                updated_params = {k: v for k, v in raw_parameters.items() if k in VALID_RESPONSE_FIELDS}
                if self._spec_manager.openapi_version.major < 3:
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
        return responses
