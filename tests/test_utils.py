from dataclasses import dataclass
from typing import Generic, TypeVar, cast
from unittest.mock import Mock, patch

import marshmallow as m
import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient
from aiohttp.web import AbstractRoute

from aiohttp_apigami.utils import (
    get_path,
    get_path_keys,
    is_class_based_view,
    resolve_schema_instance,
)


def _find_simple_route(aiohttp_app: TestClient) -> web.AbstractRoute | None:  # type: ignore[type-arg]
    """Find a route with a simple path."""
    routes = list(aiohttp_app.app.router.routes())
    for route in routes:
        if "{" in route.resource.canonical:
            return cast(web.AbstractRoute, route)
    return None


def _find_variable_route(aiohttp_app: TestClient) -> web.AbstractRoute | None:  # type: ignore[type-arg]
    """Find a route with a variable in the path."""
    routes = list(aiohttp_app.app.router.routes())
    for route in routes:
        if "{" in route.resource.canonical:
            return cast(web.AbstractRoute, route)
    return None


class TestGetPath:
    def test_get_path_from_route(self, aiohttp_app: TestClient) -> None:  # type: ignore[type-arg]
        """Test getting path from a route."""
        # Find a route with a simple path
        simple_route = _find_simple_route(aiohttp_app)

        assert simple_route is not None, "No simple route found in fixture app"
        path = get_path(simple_route)
        assert path is not None
        assert isinstance(path, str)
        assert path.startswith("/")

    def test_get_path_with_variable(self, aiohttp_app: TestClient) -> None:  # type: ignore[type-arg]
        """Test getting path with a variable."""
        # Find a route with a variable in the path
        variable_route = _find_variable_route(aiohttp_app)
        assert variable_route is not None, "No variable route found in fixture app"

        path = get_path(variable_route)
        assert path is not None
        assert "{" in path, f"Path {path} doesn't contain a variable"

    def test_get_path_from_none_resource(self) -> None:
        """Test getting path from a route with no resource."""
        # Create a mock route with a resource property that returns None
        mock_route = Mock(spec=AbstractRoute)
        mock_route.resource = None

        path = get_path(mock_route)
        assert path is None


class TestGetPathKeys:
    def test_get_path_keys_no_variables(self) -> None:
        """Test getting path keys from a path with no variables."""
        path = "/simple/path"
        keys = get_path_keys(path)
        assert keys == []

    def test_get_path_keys_with_variables(self) -> None:
        """Test getting path keys from a path with variables."""
        path = "/users/{user_id}/posts/{post_id}"
        keys = get_path_keys(path)
        assert keys == ["user_id", "post_id"]

    def test_get_path_keys_with_regex(self) -> None:
        """Test getting path keys from a path with regex."""
        path = r"/users/{user_id:\d+}/posts/{post_id:[a-z0-9]+}"
        keys = get_path_keys(path)
        assert keys == ["user_id", "post_id"]


class TestIsClassBasedView:
    def test_with_function_handler(self) -> None:
        """Test with a function handler."""

        async def handler(_: web.Request) -> web.StreamResponse:
            return web.Response(text="test")

        assert not is_class_based_view(handler)

    def test_with_class_based_view(self) -> None:
        """Test with a class-based view."""

        class TestView(web.View):
            async def get(self) -> web.StreamResponse:
                return web.Response(text="test")

        assert is_class_based_view(TestView)

    def test_with_non_view_class(self) -> None:
        """Test with a class that is not a web.View."""

        class NotAView:
            pass

        assert not is_class_based_view(NotAView)  # type: ignore[arg-type]


class TestResolveSchemaInstance:
    def test_with_schema_class(self) -> None:
        """Test with a Schema class."""

        class TestSchema(m.Schema):
            field = m.fields.String()

        schema = resolve_schema_instance(TestSchema)
        assert isinstance(schema, m.Schema)
        assert isinstance(schema, TestSchema)

    def test_with_schema_instance(self) -> None:
        """Test with a Schema instance."""

        class TestSchema(m.Schema):
            field = m.fields.String()

        schema_instance = TestSchema()
        result = resolve_schema_instance(schema_instance)
        assert result is schema_instance

    def test_with_dataclass(self) -> None:
        """Test with a dataclass."""

        @dataclass
        class TestDataclass:
            field: str

        result = resolve_schema_instance(TestDataclass)
        assert isinstance(result, m.Schema)
        # Verify the schema has the expected field with correct type
        assert "field" in result.fields
        assert isinstance(result.fields["field"], m.fields.String)

    @patch("aiohttp_apigami.utils.mr", None)
    def test_with_dataclass_no_marshmallow_recipe(self) -> None:
        """Test with a dataclass but without marshmallow-recipe."""

        @dataclass
        class TestDataclass:
            field: str

        with pytest.raises(RuntimeError, match="marshmallow-recipe is required for dataclass support"):
            resolve_schema_instance(TestDataclass)

    def test_with_generic_dataclass_alias(self) -> None:
        """Test with a generic type alias of a dataclass (e.g., MyClass = MyBaseClass[int])."""
        T = TypeVar("T")

        @dataclass
        class GenericDataclass(Generic[T]):
            value: T

        # Create a type alias with a concrete type parameter
        ConcreteAlias = GenericDataclass[int]

        result = resolve_schema_instance(ConcreteAlias)
        assert isinstance(result, m.Schema)
        # Verify the schema has the expected field with correct type
        assert "value" in result.fields
        assert isinstance(result.fields["value"], m.fields.Integer)

    def test_with_direct_generic_usage(self) -> None:
        """Test with direct generic usage (e.g., MyBaseClass[str])."""
        T = TypeVar("T")

        @dataclass
        class GenericDataclass(Generic[T]):
            value: T

        # Use the generic directly with a type parameter
        result = resolve_schema_instance(GenericDataclass[str])
        assert isinstance(result, m.Schema)
        assert "value" in result.fields
        assert isinstance(result.fields["value"], m.fields.String)

    def test_with_multiple_type_parameters(self) -> None:
        """Test with a generic dataclass that has multiple type parameters."""
        T = TypeVar("T")
        U = TypeVar("U")

        @dataclass
        class MultiGenericDataclass(Generic[T, U]):
            first: T
            second: U

        MultiAlias = MultiGenericDataclass[int, str]

        result = resolve_schema_instance(MultiAlias)
        assert isinstance(result, m.Schema)
        assert "first" in result.fields
        assert "second" in result.fields
        # Verify field types match the generic parameters
        assert isinstance(result.fields["first"], m.fields.Integer)
        assert isinstance(result.fields["second"], m.fields.String)

    def test_with_nested_generic_types(self) -> None:
        """Test with nested generic types (e.g., GenericDataclass[list[int]])."""
        T = TypeVar("T")

        @dataclass
        class GenericDataclass(Generic[T]):
            items: T

        # Test with list of integers
        ListIntAlias = GenericDataclass[list[int]]
        result = resolve_schema_instance(ListIntAlias)
        assert isinstance(result, m.Schema)
        assert "items" in result.fields
        assert isinstance(result.fields["items"], m.fields.List)

        # Test with dict
        DictAlias = GenericDataclass[dict[str, int]]
        result = resolve_schema_instance(DictAlias)
        assert isinstance(result, m.Schema)
        assert "items" in result.fields
        assert isinstance(result.fields["items"], m.fields.Dict)

    @patch("aiohttp_apigami.utils.mr", None)
    def test_with_generic_alias_no_marshmallow_recipe(self) -> None:
        """Test with a generic type alias but without marshmallow-recipe."""
        T = TypeVar("T")

        @dataclass
        class GenericDataclass(Generic[T]):
            field: T

        GenericAlias = GenericDataclass[str]

        with pytest.raises(RuntimeError, match="marshmallow-recipe is required for dataclass support"):
            resolve_schema_instance(GenericAlias)

    def test_with_invalid_schema(self) -> None:
        """Test with an invalid schema type."""
        with pytest.raises(ValueError, match="Invalid schema type:"):
            resolve_schema_instance("not a schema")  # type: ignore[arg-type]
