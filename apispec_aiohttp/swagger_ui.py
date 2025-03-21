import os
from pathlib import Path
from string import Template

from aiohttp import web

# Constants
SWAGGER_UI_STATIC_FILES = Path(__file__).parent / "swagger_ui"
SWAGGER_UI_VERSION_PATH = SWAGGER_UI_STATIC_FILES / "VERSION"
INDEX_PAGE = "index.html"

NAME_SWAGGER_SPEC = "swagger.spec"
NAME_SWAGGER_DOCS = "swagger.docs"
NAME_SWAGGER_STATIC = "swagger.static"


class SwaggerUIManager:
    """Manages the Swagger UI setup and rendering."""

    __slots__ = ("_index_page", "static_path", "url")

    def __init__(self, url: str, static_path: str = "/static/swagger"):
        self.url = url
        self.static_path = static_path
        self._index_page: str | None = None

    def setup(self, app: web.Application, swagger_path: str) -> None:
        """Set up Swagger UI routes."""
        # Add static files route
        app.router.add_static(self.static_path, SWAGGER_UI_STATIC_FILES, name=NAME_SWAGGER_STATIC)

        # Add the Swagger UI view
        async def swagger_view(_: web.Request) -> web.Response:
            index_page = self._get_index_page(app, SWAGGER_UI_STATIC_FILES)
            return web.Response(text=index_page, content_type="text/html")

        app.router.add_route("GET", swagger_path, swagger_view, name=NAME_SWAGGER_DOCS)

    def _get_index_page(self, app: web.Application, static_files: Path) -> str:
        """Get or generate the Swagger UI index page."""
        if self._index_page is not None:
            return self._index_page

        with open(str(static_files / INDEX_PAGE)) as swg_tmp:
            url = str(app.router[NAME_SWAGGER_SPEC].url_for())

            static_url = app.router[NAME_SWAGGER_STATIC].url_for(filename=INDEX_PAGE)
            static_path = os.path.dirname(str(static_url))

            self._index_page = Template(swg_tmp.read()).substitute(
                path=url,
                static=static_path,
            )

        assert self._index_page is not None  # for mypy
        return self._index_page
