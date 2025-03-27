import copy
from typing import Any

import marshmallow as m
from apispec.core import VALID_METHODS
from apispec.ext.marshmallow import MarshmallowPlugin

from aiohttp_apigami.constants import API_SPEC_ATTR
from aiohttp_apigami.typedefs import HandlerType
from aiohttp_apigami.utils import get_path_keys

_BODY_LOCATIONS = {"body", "json"}


class ApigamiPlugin(MarshmallowPlugin):
    def _path_parameters(self, path_key: str) -> dict[str, Any]:
        """
        Create path parameters based on OpenAPI/Swagger spec.

        Generates parameter definitions for URL path parameters in the format
        required by either OpenAPI v2 or v3, depending on the configured version.

        Args:
            path_key: The name of the path parameter from the URL pattern

        Returns:
            A dictionary containing the path parameter definition
        """
        assert self.openapi_version is not None, "init_spec has not yet been called"

        # OpenAPI v2
        if self.openapi_version.major < 3:
            return {"in": "path", "name": path_key, "required": True, "type": "string"}

        # OpenAPI v3
        return {"in": "path", "name": path_key, "required": True, "schema": {"type": "string"}}

    def _response_parameters(self, schema: m.Schema) -> dict[str, Any]:
        """
        Create response parameters based on OpenAPI/Swagger spec.

        Generates response parameter definitions in the format required by either
        OpenAPI v2 or v3, depending on the configured version. In v2, the schema
        is directly included, while in v3 it's nested under content/application/json.

        Args:
            schema: A Marshmallow schema instance that defines the response structure

        Returns:
            A dictionary containing the response parameter definition
        """
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
        """
        Add examples to schema or endpoint for OpenAPI spec.

        Adds provided example data to either a schema reference or parameter list.
        Behavior varies depending on OpenAPI version (v2 or v3) and whether
        the example should be added to a schema reference or inline.

        Args:
            schema_instance: The Marshmallow schema instance
            example: The example data to add (if None, no example is added)
            parameters: List of parameter definitions to potentially add the example to
        """
        assert self.spec is not None, "init_spec has not yet been called"
        assert self.openapi_version is not None, "init_spec has not yet been called"
        assert self.converter is not None, "init_spec has not yet been called"

        if not example:
            return

        schema_name = self.converter.schema_name_resolver(schema_instance)
        add_to_refs = example.pop("add_to_refs", False)

        if add_to_refs and schema_name in self.spec.components.schemas:
            self.spec.components.schemas[schema_name]["example"] = example
        elif parameters:
            # Get the reference path from $ref field
            ref_path = parameters[0]["schema"].pop("$ref")
            parameters[0]["schema"]["allOf"] = [{"$ref": ref_path}]
            parameters[0]["schema"]["example"] = example

    def _process_body(self, schema: dict[str, Any], method_operation: dict[str, Any]) -> None:
        """
        Process request body for OpenAPI spec.

        Extracts and formats request body schemas for OpenAPI documentation.
        For v2, adds body schemas as parameters.
        For v3, processes body schemas into requestBody format.

        Args:
            schema: The schema definition including location and schema instance
            method_operation: The operation dictionary to update with body parameters
        """
        assert self.openapi_version is not None, "init_spec has not yet been called"
        assert self.converter is not None, "init_spec has not yet been called"

        method_operation["parameters"] = method_operation.get("parameters", [])

        location = schema["location"]
        if location not in _BODY_LOCATIONS:
            # Process only json location
            return

        schema_instance = schema["schema"]

        # OpenAPI v2: body/json is a part of parameters
        if self.openapi_version.major < 3:
            body_parameters = self.converter.schema2parameters(
                schema=schema_instance, location=location, **schema["options"]
            )
            method_operation["parameters"].extend(body_parameters)

        # OpenAPI v3: body/json is requestBody object
        else:
            body_parameters = None
            method_operation["requestBody"] = {
                "content": {"application/json": {"schema": schema_instance}},
                **schema["options"],
            }

        # Add example for all OpenAPI versions
        self._add_example(schema_instance=schema_instance, parameters=body_parameters, example=schema.get("example"))

    def _get_method_operation(self, handler_spec: dict[str, Any]) -> dict[str, Any]:
        """
        Process request schemas for OpenAPI spec. Returns operation object.

        Builds a complete operation object with parameters derived from handler
        schemas and explicit parameters. Handles both body and non-body parameters
        according to OpenAPI spec version rules.

        Args:
            handler_spec: The handler function's spec metadata containing schemas and parameters

        Returns:
            Dictionary with parameters and other operation components
        """
        assert self.converter is not None, "init_spec has not yet been called"
        assert self.openapi_version is not None, "init_spec has not yet been called"

        # Set existing parameters
        operation: dict[str, Any] = {"parameters": copy.deepcopy(handler_spec["parameters"])}

        # Add parameters from schemas
        for schema in handler_spec["schemas"]:
            location = schema["location"]
            if location in _BODY_LOCATIONS:
                # Body parameter is located in different place for v2 and v3
                # Let's process it separately
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

    def _process_responses(self, handler_spec: dict[str, Any], method_operation: dict[str, Any]) -> None:
        """
        Process response schemas for OpenAPI spec.

        Extracts response schemas from handler metadata and adds them to the
        operation object in the format required by the configured OpenAPI version.
        Preserves additional response metadata like descriptions and headers.

        Args:
            handler_spec: The handler function's spec metadata containing schemas and parameters
            method_operation: The operation object to update with response information
        """
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
    def _process_extra_options(handler_spec: dict[str, Any], method_operation: dict[str, Any]) -> None:
        """
        Process extra options for OpenAPI spec.

        Extracts and adds any additional metadata from handler spec that isn't
        specifically related to schemas, responses, or parameters.

        Args:
            handler_spec: The handler function's spec metadata containing schemas and parameters
            method_operation: The operation object to update with additional options
        """
        for key, value in handler_spec.items():
            if key not in ("schemas", "responses", "parameters"):
                method_operation[key] = value

    def _process_path_parameters(self, path: str, method_operation: dict[str, Any]) -> None:
        """
        Process path parameters for OpenAPI spec.

        Identifies URL path parameters (like /users/{id}) and adds corresponding
        parameter definitions to the operation if they don't already exist.

        Args:
            path: The URL path pattern that may contain parameters in {brackets}
            method_operation: The operation object to update with path parameters
        """
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
        method: str | None = None,
        handler: HandlerType | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Path helper that processes route data for OpenAPI documentation.

        This is the main entry point for apispec that converts an aiohttp route
        into an OpenAPI path definition. It extracts all metadata from the route handler,
        processes parameters, responses, and other documentation details, and
        formats them according to the OpenAPI specification version.

        Args:
            path: The URL path pattern that may contain parameters in {brackets}
            operations: Dictionary to update with operation definitions
            parameters: List of global parameters applicable to all operations
            method: HTTP method (get, post, put, etc.) for the operation
            handler: The request handler function with API spec metadata
            **kwargs: Additional arguments passed by apispec

        Returns:
            The processed path

        Raises:
            RuntimeError: If the HTTP method is not supported by the OpenAPI specification version
            AssertionError: If any required parameters are missing
        """
        assert self.openapi_version is not None, "init_spec has not yet been called"
        assert operations is not None
        assert parameters is not None

        # Validate that we have all required parameters
        assert path is not None, "Missing 'path' parameter"
        assert method is not None, "Missing 'method' parameter"
        assert handler is not None, "Missing 'handler' parameter"

        # Do nothing if is spec is not enabled
        handler_spec = getattr(handler, API_SPEC_ATTR, {})
        if not handler_spec:
            return path

        # Check if method is valid for the current OpenAPI version
        valid_methods = VALID_METHODS[self.openapi_version.major]
        if method.lower() not in valid_methods:
            raise RuntimeError(f"Method {method!r} not supported by OpenAPI spec version {self.openapi_version}")

        # Build the method operation object
        method_operation = self._get_method_operation(handler_spec)

        # Process path parameters
        self._process_path_parameters(path=path, method_operation=method_operation)

        # Process response schemas
        self._process_responses(handler_spec, method_operation)

        # Process additional options (tags, summary, etc.)
        self._process_extra_options(handler_spec, method_operation)

        # Add the operation to the operations dictionary
        operations[method.lower()] = method_operation

        return path
