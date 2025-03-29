from unittest.mock import mock_open, patch

import pytest
from aiohttp import web

from aiohttp_apigami.swagger_ui import (
    INDEX_PAGE,
    NAME_SWAGGER_SPEC,
    NAME_SWAGGER_STATIC,
    SWAGGER_UI_STATIC_FILES,
    LayoutOption,
    SwaggerUIManager,
)

# Test constants
TEST_SWAGGER_URL = "/api/swagger.json"
TEST_SWAGGER_PATH = "/docs"
TEST_STATIC_PATH = "/static/swagger"


@pytest.fixture
def swagger_app() -> web.Application:
    """Create a test application with necessary routes."""
    app = web.Application()

    # Setup routes needed for testing
    async def dummy_handler(request: web.Request) -> web.Response:
        return web.Response(text="")

    # Add required routes to the application
    app.router.add_get(TEST_SWAGGER_URL, dummy_handler, name=NAME_SWAGGER_SPEC)
    app.router.add_static(TEST_STATIC_PATH, SWAGGER_UI_STATIC_FILES, name=NAME_SWAGGER_STATIC)

    return app


def test_index_page_caching(swagger_app: web.Application) -> None:
    """Test that _get_index_page caches and returns the _index_page when it's not None."""
    # Initialize the manager
    manager = SwaggerUIManager(url=TEST_SWAGGER_URL, static_path=TEST_STATIC_PATH)

    # Mock content with placeholders for substitution
    mock_content = "layout=${layout}\npath=${path}\nstatic=${static}"
    mock_file = mock_open(read_data=mock_content)

    with patch("builtins.open", mock_file):
        # First call should read from file
        first_result = manager._get_index_page(swagger_app, SWAGGER_UI_STATIC_FILES)

        # Verify file was read correctly
        mock_file.assert_called_once_with(str(SWAGGER_UI_STATIC_FILES / INDEX_PAGE))

        # Reset the mock to verify it's not called again
        mock_file.reset_mock()

        # Second call should use cached value
        second_result = manager._get_index_page(swagger_app, SWAGGER_UI_STATIC_FILES)

        # Verify the file was not read again (caching works)
        mock_file.assert_not_called()

        # Results should be identical (cached value used)
        assert first_result == second_result

        # Verify content substitution
        assert LayoutOption.Standalone.value in first_result
        assert TEST_SWAGGER_URL in first_result
