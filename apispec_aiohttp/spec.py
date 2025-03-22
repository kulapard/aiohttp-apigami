from typing import Any

from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from packaging.version import Version

from .typedefs import SchemaNameResolver, SchemaType


class SpecManager:
    """Manages the OpenAPI specification creation and manipulation."""

    __slots__ = ("_plugin", "_spec")

    def __init__(
        self,
        openapi_version: str,
        schema_name_resolver: SchemaNameResolver,
        **kwargs: Any,
    ):
        self._plugin = MarshmallowPlugin(schema_name_resolver=schema_name_resolver)
        self._spec = APISpec(
            plugins=(self._plugin,),
            openapi_version=openapi_version,
            **kwargs,
        )

    @property
    def plugin(self) -> MarshmallowPlugin:
        """Get access to the MarshmallowPlugin."""
        return self._plugin

    @property
    def spec(self) -> APISpec:
        """Get access to the APISpec."""
        return self._spec

    def swagger_dict(self) -> dict[str, Any]:
        """Returns swagger spec representation in JSON format"""
        return self._spec.to_dict()

    def add_path(self, *, path: str, method: str, handler_apispec: dict[str, Any]) -> None:
        """Add a new path to the spec."""
        self._spec.path(path=path, operations={method: handler_apispec})

    @property
    def schemas(self) -> dict[str, dict[str, Any]]:
        """Get access to spec schemas.

        This is a wrapper around the spec.components.schemas dictionary property.
        """
        return self._spec.components.schemas

    @property
    def openapi_version(self) -> Version:
        """Get access to spec's OpenAPI version.

        This is a wrapper around the spec.components.openapi_version property.
        """
        return self._spec.components.openapi_version

    def schema2parameters(self, schema: SchemaType, location: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Convert a schema to OpenAPI parameters.

        This is a wrapper around the plugin's converter.schema2parameters method.
        """
        parameters = self._plugin.converter.schema2parameters(  # type: ignore[union-attr]
            schema=schema, location=location, **kwargs
        )
        return parameters  # type: ignore[no-any-return]

    def get_schema_name(self, schema_instance: Any) -> str:
        """Get the schema name using the configured resolver.

        This is a wrapper around the plugin's converter.schema_name_resolver method.
        """
        schema_name = self._plugin.converter.schema_name_resolver(schema_instance)  # type: ignore[union-attr]
        return schema_name  # type: ignore[no-any-return]
