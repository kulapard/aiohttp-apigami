import copy
from typing import Any

from aiohttp import web
from aiohttp.hdrs import METH_ALL, METH_ANY
from apispec.core import VALID_METHODS_OPENAPI_V2
from apispec.ext.marshmallow import common

from .spec import SpecManager
from .typedefs import AiohttpView, SchemaType
from .utils import get_path, get_path_keys, is_class_based_view

VALID_RESPONSE_FIELDS = {"description", "headers", "examples"}
DEFAULT_RESPONSE_LOCATION = "json"


class RouteProcessor:
    """Processes aiohttp routes to extract OpenAPI data."""

    __slots__ = ("prefix", "spec_manager")

    def __init__(self, spec_manager: SpecManager, prefix: str = ""):
        self.spec_manager = spec_manager
        self.prefix = prefix

    def schema2parameters(self, *, schema: SchemaType, location: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Convert a schema to OpenAPI parameters."""
        return self.spec_manager.schema2parameters(schema, location=location, **kwargs)

    def add_examples(
        self, *, ref_schema: SchemaType, endpoint_schema: list[dict[str, Any]], example: dict[str, Any] | None
    ) -> None:
        """Add examples to schema or endpoint."""
        if not example:
            return

        schema_instance = common.resolve_schema_instance(ref_schema)
        name = self.spec_manager.get_schema_name(schema_instance)
        add_to_refs = example.pop("add_to_refs", False)  # Default to False if key doesn't exist

        def add_to_endpoint_or_ref() -> None:
            if add_to_refs and name is not None:
                self.spec_manager.schemas[name]["example"] = example
            else:
                # Get the reference path from $ref field
                ref_path = endpoint_schema[0]["schema"].pop("$ref")
                # Ensure there's no duplication of #/definitions/
                if "#/definitions/#/definitions/" in ref_path:
                    ref_path = ref_path.replace("#/definitions/#/definitions/", "#/definitions/")
                endpoint_schema[0]["schema"]["allOf"] = [{"$ref": ref_path}]
                endpoint_schema[0]["schema"]["example"] = example

        if self.spec_manager.openapi_version.major < 3:
            if name and name in self.spec_manager.schemas:
                add_to_endpoint_or_ref()
        else:
            add_to_endpoint_or_ref()

    def register_routes(self, app: web.Application) -> None:
        """Register all routes from the application."""
        for route in app.router.routes():
            if is_class_based_view(route.handler) and route.method == METH_ANY:
                for attr in dir(route.handler):
                    if attr.upper() in METH_ALL:
                        view = getattr(route.handler, attr)
                        method = attr
                        self.register_route(route, method, view)
            else:
                method = route.method.lower()
                view = route.handler
                self.register_route(route, method, view)

    def register_route(self, route: web.AbstractRoute, method: str, view: AiohttpView) -> None:
        """Register a single route."""
        if not hasattr(view, "__apispec__"):
            return None

        url_path = get_path(route)
        if not url_path:
            return None

        view_apispec = getattr(view, "__apispec__", {})
        self.update_paths(view_apispec, method, self.prefix + url_path)

    def update_paths(self, view_apispec: dict[str, Any], method: str, url_path: str) -> None:
        """Update spec paths with route information."""
        if method not in VALID_METHODS_OPENAPI_V2:
            return None

        for schema in view_apispec.pop("schemas", []):
            parameters = self.schema2parameters(
                schema=schema["schema"], location=schema["location"], **schema["options"]
            )
            self.add_examples(ref_schema=schema["schema"], endpoint_schema=parameters, example=schema["example"])
            view_apispec["parameters"].extend(parameters)

        existing = [p["name"] for p in view_apispec["parameters"] if p["in"] == "path"]
        view_apispec["parameters"].extend(
            {"in": "path", "name": path_key, "required": True, "type": "string"}
            for path_key in get_path_keys(url_path)
            if path_key not in existing
        )

        if "responses" in view_apispec:
            view_apispec["responses"] = self._process_responses(view_apispec["responses"])

        view_apispec = copy.deepcopy(view_apispec)
        self.spec_manager.update_path(path=url_path, method=method, view_apispec=view_apispec)

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
                if self.spec_manager.openapi_version.major < 3:
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
