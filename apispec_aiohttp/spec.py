from typing import Any

from apispec import APISpec
from apispec.core import Components
from apispec.ext.marshmallow import MarshmallowPlugin

from .typedefs import SchemaNameResolver


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

    def update_path(self, *, path: str, method: str, view_apispec: dict[str, Any]) -> None:
        """Add a new path to the spec."""
        self._spec.path(path=path, operations={method: view_apispec})

    @property
    def components(self) -> Components:
        """Get access to spec components."""
        return self._spec.components

    @property
    def schemas(self) -> dict[str, Any]:
        """Get access to spec schemas.

        This is a wrapper around the spec.components.schemas dictionary.
        """
        return self._spec.components.schemas

    @property
    def openapi_version(self) -> Any:
        """Get access to spec's OpenAPI version.

        This is a wrapper around the spec.components.openapi_version property.
        """
        return self._spec.components.openapi_version

    def schema2parameters(self, schema: Any, location: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Convert a schema to OpenAPI parameters.

        This is a wrapper around the plugin's converter.schema2parameters method.
        """
        result = self._plugin.converter.schema2parameters(  # type: ignore[union-attr]
            schema, location=location, **kwargs
        )
        return result  # type: ignore[no-any-return]

    def get_schema_name(self, schema_instance: Any) -> str:
        """Get the schema name using the configured resolver.

        This is a wrapper around the plugin's converter.schema_name_resolver method.
        """
        result = self._plugin.converter.schema_name_resolver(schema_instance)  # type: ignore[union-attr]
        return result  # type: ignore[no-any-return]
