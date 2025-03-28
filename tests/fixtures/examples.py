from typing import Any

import pytest


@pytest.fixture
def example_for_request_schema() -> dict[str, Any]:
    return {
        "id": 1,
        "name": "test",
        "bool_field": True,
        "list_field": [1, 2, 3],
        "nested_field": {"i": 12},
    }


@pytest.fixture
def example_for_request_dataclass() -> dict[str, Any]:
    return {
        "id": 2,
        "name": "dataclass_test",
        "bool_field": True,
        "list_field": [4, 5, 6],
        "nested_field": {"i": 42},
    }
