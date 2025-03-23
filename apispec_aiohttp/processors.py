import copy
from abc import ABC, abstractmethod
from typing import Any

from apispec.core import VALID_METHODS_OPENAPI_V2, VALID_METHODS_OPENAPI_V3
from apispec.ext.marshmallow import common

from .spec import SpecManager
from .typedefs import SchemaType
from .utils import get_path_keys

VALID_RESPONSE_FIELDS = {"description", "headers", "examples"}
DEFAULT_RESPONSE_LOCATION = "json"


class BaseOpenAPIProcessor(ABC):
    """Base class for OpenAPI version-specific processors."""

    def __init__(self, spec_manager: SpecManager):
        self._spec_manager = spec_manager

    @abstractmethod
    def get_path_method_spec(self, *, path: str, method: str, handler_apispec: dict[str, Any]) -> dict[str, Any] | None:
        """Get path operations based on OpenAPI version."""
        ...


class OpenAPIv2Processor(BaseOpenAPIProcessor):
    """Processor for OpenAPI v2.x specifications."""

    def get_path_method_spec(self, *, path: str, method: str, handler_apispec: dict[str, Any]) -> dict[str, Any] | None:
        if method not in VALID_METHODS_OPENAPI_V2:
            return None

        for schema in handler_apispec.pop("schemas", []):
            schema_instance = schema["schema"]
            parameters = self._spec_manager.schema2parameters(
                schema=schema_instance, location=schema["location"], **schema["options"]
            )
            self._add_example(schema=schema_instance, parameters=parameters, example=schema["example"])
            handler_apispec["parameters"].extend(parameters)

        # Update path keys if they are not already present in the handler_apispec
        existing_path_keys = {p["name"] for p in handler_apispec["parameters"] if p["in"] == "path"}
        new_path_keys = (path_key for path_key in get_path_keys(path) if path_key not in existing_path_keys)
        new_path_params = [self._path_parameters(path_key) for path_key in new_path_keys]
        handler_apispec["parameters"].extend(new_path_params)

        # Process responses using the version-specific processor
        if "responses" in handler_apispec:
            handler_apispec["responses"] = self._process_responses(handler_apispec["responses"])

        return copy.deepcopy(handler_apispec)

    def _add_example(
        self, schema: SchemaType, parameters: list[dict[str, Any]], example: dict[str, Any] | None
    ) -> None:
        """Add examples to schema or endpoint for OpenAPI v2."""
        if not example:
            return

        schema_instance = common.resolve_schema_instance(schema)
        schema_name = self._spec_manager.get_schema_name(schema_instance)
        add_to_refs = example.pop("add_to_refs", False)

        if schema_name and schema_name in self._spec_manager.schemas:
            self._add_example_to_schema(schema_name, parameters, example, add_to_refs)

    def _add_example_to_schema(
        self, schema_name: str, parameters: list[dict[str, Any]], example: dict[str, Any], add_to_refs: bool
    ) -> None:
        """Helper method to add example to schema for v2."""
        if add_to_refs:
            self._spec_manager.schemas[schema_name]["example"] = example
        else:
            # Get the reference path from $ref field
            ref_path = parameters[0]["schema"].pop("$ref")
            # Ensure there's no duplication of #/definitions/
            if "#/definitions/#/definitions/" in ref_path:
                ref_path = ref_path.replace("#/definitions/#/definitions/", "#/definitions/")
            parameters[0]["schema"]["allOf"] = [{"$ref": ref_path}]
            parameters[0]["schema"]["example"] = example

    def _process_responses(self, responses_data: dict[str, Any]) -> dict[str, Any]:
        """Process response schemas for OpenAPI v2 spec."""
        responses = {}
        for code, actual_params in responses_data.items():
            if "schema" in actual_params:
                raw_parameters = self._spec_manager.schema2parameters(
                    schema=actual_params["schema"],
                    location=DEFAULT_RESPONSE_LOCATION,
                    required=actual_params.get("required", False),
                )[0]
                updated_params = {k: v for k, v in raw_parameters.items() if k in VALID_RESPONSE_FIELDS}
                # OpenAPI v2 specific format
                updated_params["schema"] = actual_params["schema"]

                for extra_info in ("description", "headers", "examples"):
                    if extra_info in actual_params:
                        updated_params[extra_info] = actual_params[extra_info]
                responses[code] = updated_params
            else:
                responses[code] = actual_params
        return responses

    @staticmethod
    def _path_parameters(path_key: str) -> dict[str, Any]:
        """Create path parameters based on OpenAPI v2 spec."""
        return {"in": "path", "name": path_key, "required": True, "type": "string"}


class OpenAPIv3Processor(BaseOpenAPIProcessor):
    """Processor for OpenAPI v3.x specifications."""

    def get_path_method_spec(self, *, path: str, method: str, handler_apispec: dict[str, Any]) -> dict[str, Any] | None:
        if method not in VALID_METHODS_OPENAPI_V3:
            return None

        for schema in handler_apispec.pop("schemas", []):
            schema_instance = schema["schema"]
            parameters = self._spec_manager.schema2parameters(
                schema=schema_instance, location=schema["location"], **schema["options"]
            )
            self._add_example(schema=schema_instance, parameters=parameters, example=schema["example"])
            handler_apispec["parameters"].extend(parameters)

        # Update path keys if they are not already present in the handler_apispec
        existing_path_keys = {p["name"] for p in handler_apispec["parameters"] if p["in"] == "path"}
        new_path_keys = (path_key for path_key in get_path_keys(path) if path_key not in existing_path_keys)
        new_path_params = [self._path_parameters(path_key) for path_key in new_path_keys]
        handler_apispec["parameters"].extend(new_path_params)

        # Process responses using the version-specific processor
        if "responses" in handler_apispec:
            handler_apispec["responses"] = self._process_responses(handler_apispec["responses"])

        return copy.deepcopy(handler_apispec)

    def _add_example(
        self, schema: SchemaType, parameters: list[dict[str, Any]], example: dict[str, Any] | None
    ) -> None:
        """Add examples to schema or endpoint for OpenAPI v3."""
        if not example:
            return

        schema_instance = common.resolve_schema_instance(schema)
        schema_name = self._spec_manager.get_schema_name(schema_instance)
        add_to_refs = example.pop("add_to_refs", False)

        # In v3, we always add the example regardless of schema being in schemas
        self._add_example_to_schema(schema_name, parameters, example, add_to_refs)

    def _add_example_to_schema(
        self, schema_name: str, parameters: list[dict[str, Any]], example: dict[str, Any], add_to_refs: bool
    ) -> None:
        """Helper method to add example to schema for v3."""
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

    def _process_responses(self, responses_data: dict[str, Any]) -> dict[str, Any]:
        """Process response schemas for OpenAPI v3 spec."""
        responses = {}
        for code, actual_params in responses_data.items():
            if "schema" in actual_params:
                raw_parameters = self._spec_manager.schema2parameters(
                    schema=actual_params["schema"],
                    location=DEFAULT_RESPONSE_LOCATION,
                    required=actual_params.get("required", False),
                )[0]
                updated_params = {k: v for k, v in raw_parameters.items() if k in VALID_RESPONSE_FIELDS}
                # OpenAPI v3 specific content format
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

    @staticmethod
    def _path_parameters(path_key: str) -> dict[str, Any]:
        """Create path parameters based on OpenAPI v3 spec."""
        return {"in": "path", "name": path_key, "required": True, "schema": {"type": "string"}}


def create_processor(spec_manager: SpecManager) -> BaseOpenAPIProcessor:
    """Create an appropriate processor based on OpenAPI version."""
    version = spec_manager.openapi_version

    if version.major < 3:
        return OpenAPIv2Processor(spec_manager)
    else:
        return OpenAPIv3Processor(spec_manager)
