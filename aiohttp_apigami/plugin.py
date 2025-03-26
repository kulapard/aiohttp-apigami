import copy
from typing import Any

import marshmallow as m
from apispec.core import VALID_METHODS
from apispec.ext.marshmallow import MarshmallowPlugin

from aiohttp_apigami.constants import API_SPEC_ATTR
from aiohttp_apigami.data import RouteData
from aiohttp_apigami.typedefs import HandlerType
from aiohttp_apigami.utils import get_path_keys

_BODY_LOCATIONS = {"body", "json"}


class ApigamiPlugin(MarshmallowPlugin):
    def _path_parameters(self, path_key: str) -> dict[str, Any]:
        """Create path parameters based on OpenAPI/Swagger spec."""
        assert self.openapi_version is not None, "init_spec has not yet been called"

        # OpenAPI v2
        if self.openapi_version.major < 3:
            return {"in": "path", "name": path_key, "required": True, "type": "string"}

        # OpenAPI v3
        return {"in": "path", "name": path_key, "required": True, "schema": {"type": "string"}}

    def _response_parameters(self, schema: m.Schema) -> dict[str, Any]:
        """Create response parameters based on OpenAPI/Swagger spec."""
        assert self.openapi_version is not None, "init_spec has not yet been called"

        # OpenAPI v2
        if self.openapi_version.major < 3:
            return {"schema": schema}

        # OpenAPI v3
        return {
            "content": {
                "application/json": {
                    "schema": schema,
                },
            }
        }

    def _add_example(
        self, schema_instance: m.Schema, parameters: list[dict[str, Any]], example: dict[str, Any] | None
    ) -> None:
        """Add examples to schema or endpoint for OpenAPI v3."""
        assert self.spec is not None, "init_spec has not yet been called"
        assert self.openapi_version is not None, "init_spec has not yet been called"
        assert self.converter is not None, "init_spec has not yet been called"

        if not example:
            return

        schema_name = self.converter.schema_name_resolver(schema_instance)
        add_to_refs = example.pop("add_to_refs", False)

        # v2: Add example to schema if schema is in schemas
        if self.openapi_version.major < 3:
            if schema_name in self.spec.components.schemas:
                self._add_example_to_schema(schema_name, parameters, example, add_to_refs)
        else:
            # v3: Always add the example regardless of schema being in schemas
            self._add_example_to_schema(schema_name, parameters, example, add_to_refs)

    def _add_example_to_schema(
        self, schema_name: str, parameters: list[dict[str, Any]], example: dict[str, Any], add_to_refs: bool
    ) -> None:
        """Helper method to add example to schema for v3."""
        assert self.spec is not None, "init_spec has not yet been called"

        if add_to_refs and schema_name is not None:
            self.spec.components.schemas[schema_name]["example"] = example
        elif parameters:
            # Get the reference path from $ref field
            ref_path = parameters[0]["schema"].pop("$ref")
            # Ensure there's no duplication of #/definitions/
            if "#/definitions/#/definitions/" in ref_path:
                ref_path = ref_path.replace("#/definitions/#/definitions/", "#/definitions/")
            parameters[0]["schema"]["allOf"] = [{"$ref": ref_path}]
            parameters[0]["schema"]["example"] = example

    def _process_body(self, handler: HandlerType) -> dict[str, Any]:
        """Process request body for OpenAPI v3 spec."""
        assert self.openapi_version is not None, "init_spec has not yet been called"

        if self.openapi_version.major < 3:
            # v2: body/json is processed as part of parameters
            return {}

        handler_spec = getattr(handler, API_SPEC_ATTR, {})
        if not handler_spec:
            return {}

        # Find the first body schema
        for schema in handler_spec["schemas"]:
            if schema["location"] in _BODY_LOCATIONS:
                return {
                    "requestBody": {"content": {"application/json": {"schema": schema["schema"]}}, **schema["options"]}
                }

        return {}

    def _process_parameters(self, handler: HandlerType) -> list[dict[str, Any]]:
        """Process request schemas for OpenAPI spec."""
        assert self.converter is not None, "init_spec has not yet been called"
        assert self.openapi_version is not None, "init_spec has not yet been called"

        handler_spec = getattr(handler, API_SPEC_ATTR, {})
        if not handler_spec:
            return []

        parameters: list[dict[Any, Any]] = copy.deepcopy(handler_spec["parameters"])

        for schema in handler_spec["schemas"]:
            location = schema["location"]
            if self.openapi_version.major >= 3 and location in _BODY_LOCATIONS:
                # Skip body schema as it is processed separately
                continue

            example = schema["example"]
            schema_instance = schema["schema"]
            schema_parameters = self.converter.schema2parameters(
                schema=schema_instance, location=location, **schema["options"]
            )
            self._add_example(schema_instance=schema_instance, parameters=schema_parameters, example=example)
            parameters.extend(schema_parameters)
        return parameters

    def _process_responses(self, handler: HandlerType) -> dict[str, Any]:
        """Process response schemas for OpenAPI spec."""
        handler_spec = getattr(handler, API_SPEC_ATTR, {})
        if not handler_spec:
            return {}

        responses_data = handler_spec.get("responses")
        if not responses_data:
            return {}

        responses = {}
        for code, actual_params in responses_data.items():
            if "schema" in actual_params:
                response_params = self._response_parameters(actual_params["schema"])
                for extra_info in ("description", "headers", "examples"):
                    if extra_info in actual_params:
                        response_params[extra_info] = actual_params[extra_info]
                responses[code] = response_params
            else:
                responses[code] = actual_params
        return responses

    @staticmethod
    def _process_extra_options(handler: HandlerType) -> dict[str, Any]:
        """Process extra options for OpenAPI spec."""
        handler_spec = getattr(handler, API_SPEC_ATTR, {})
        if not handler_spec:
            return {}

        other_options = {}
        for key, value in handler_spec.items():
            if key not in ("schemas", "responses", "parameters"):
                other_options[key] = value

        return other_options

    def path_helper(
        self,
        path: str | None = None,
        operations: dict[Any, Any] | None = None,
        parameters: list[dict[Any, Any]] | None = None,
        *,
        route: RouteData | None = None,
        **kwargs: Any,
    ) -> str | None:
        """Path helper that allows using an aiohttp AbstractRoute in path definition."""
        assert self.openapi_version is not None, "init_spec has not yet been called"
        assert operations is not None
        assert parameters is not None
        assert route is not None

        valid_methods = VALID_METHODS[self.openapi_version.major]
        if route.method not in valid_methods:
            return route.path

        # Request parameters
        request_parameters = self._process_parameters(route.handler)

        # Response parameters
        responses = self._process_responses(route.handler)

        # Body parameters
        body_parameters = self._process_body(route.handler)

        # Other options
        extra_options = self._process_extra_options(route.handler)

        # Combine all parameters into one list:
        # [{method: {responses: {}, parameters: [], ...}}]
        operations.update(
            {
                route.method.lower(): {
                    "responses": responses,
                    "parameters": request_parameters,
                    **body_parameters,
                    **extra_options,
                }
            }
        )

        # Update path keys if they are not already present in the handler_apispec (from match_info schema)
        existing_path_keys = {p["name"] for p in parameters if p["in"] == "path"}
        new_path_keys = (path_key for path_key in get_path_keys(route.path) if path_key not in existing_path_keys)
        new_path_params = [self._path_parameters(path_key) for path_key in new_path_keys]
        parameters.extend(new_path_params)

        return route.path
