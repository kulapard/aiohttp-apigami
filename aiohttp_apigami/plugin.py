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
        self,
        schema_instance: m.Schema,
        example: dict[str, Any] | None,
        parameters: list[dict[str, Any]] | None = None,
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
        self, schema_name: str, parameters: list[dict[str, Any]] | None, example: dict[str, Any], add_to_refs: bool
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

    def _process_body(self, schema: dict[str, Any], method_operation: dict[str, Any]) -> None:
        """Process request body for OpenAPI spec."""
        assert self.openapi_version is not None, "init_spec has not yet been called"
        assert self.converter is not None, "init_spec has not yet been called"

        method_operation["parameters"] = method_operation.get("parameters", [])

        location = schema["location"]
        if location not in _BODY_LOCATIONS:
            # Process only json location
            return

        schema_instance = schema["schema"]

        # v2: body/json is processed as part of parameters
        if self.openapi_version.major < 3:
            body_parameters = self.converter.schema2parameters(
                schema=schema_instance, location=location, **schema["options"]
            )
            self._add_example(
                schema_instance=schema_instance, parameters=body_parameters, example=schema.get("example")
            )
            method_operation["parameters"].extend(body_parameters)

        # v3: body/json is processed as requestBody
        else:
            self._add_example(schema_instance=schema_instance, example=schema.get("example"))
            method_operation["requestBody"] = {
                "content": {"application/json": {"schema": schema_instance}},
                **schema["options"],
            }

    def _get_method_operation(self, handler: HandlerType) -> dict[str, Any]:
        """Process request schemas for OpenAPI spec. Returns operation object."""
        assert self.converter is not None, "init_spec has not yet been called"
        assert self.openapi_version is not None, "init_spec has not yet been called"

        handler_spec = getattr(handler, API_SPEC_ATTR, {})
        if not handler_spec:
            return {}

        # Set existing parameters
        operation: dict[str, Any] = {"parameters": copy.deepcopy(handler_spec["parameters"])}

        # Add parameters from schemas
        for schema in handler_spec["schemas"]:
            location = schema["location"]
            if location in _BODY_LOCATIONS:
                # Single body parameter is located in different place for v2 and v3
                # process it separately
                self._process_body(schema=schema, method_operation=operation)
            else:
                example = schema.get("example")
                schema_instance = schema["schema"]
                schema_parameters = self.converter.schema2parameters(
                    schema=schema_instance, location=location, **schema["options"]
                )
                self._add_example(schema_instance=schema_instance, parameters=schema_parameters, example=example)
                operation["parameters"].extend(schema_parameters)

        return operation

    def _process_responses(self, handler: HandlerType, method_operation: dict[str, Any]) -> None:
        """Process response schemas for OpenAPI spec."""
        handler_spec = getattr(handler, API_SPEC_ATTR, {})
        if not handler_spec:
            return None

        method_operation["responses"] = method_operation.get("responses", {})

        responses_data = handler_spec.get("responses", {})
        if not responses_data:
            return None

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

        method_operation["responses"].update(responses)

    @staticmethod
    def _process_extra_options(handler: HandlerType, method_operation: dict[str, Any]) -> None:
        """Process extra options for OpenAPI spec."""
        handler_spec = getattr(handler, API_SPEC_ATTR, {})
        if not handler_spec:
            return None

        for key, value in handler_spec.items():
            if key not in ("schemas", "responses", "parameters"):
                method_operation[key] = value

    def _process_path_parameters(self, path: str, method_operation: dict[str, Any]) -> None:
        """Process path parameters for OpenAPI spec."""
        assert self.openapi_version is not None, "init_spec has not yet been called"

        method_parameters = method_operation["parameters"]

        path_keys = get_path_keys(path)
        existing_path_keys = {p["name"] for p in method_parameters if p["in"] == "path"}
        new_path_keys = (k for k in path_keys if k not in existing_path_keys)
        new_path_params = [self._path_parameters(path_key) for path_key in new_path_keys]
        method_parameters.extend(new_path_params)

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

        # Request
        method_operation = self._get_method_operation(route.handler)

        # Path parameters
        self._process_path_parameters(path=route.path, method_operation=method_operation)

        # Response
        self._process_responses(route.handler, method_operation)

        # Extra options
        self._process_extra_options(route.handler, method_operation)

        # Combine all method parameters and responses
        # [{method: {responses: {}, parameters: [], ...}}]
        operations[route.method] = method_operation
        return route.path
