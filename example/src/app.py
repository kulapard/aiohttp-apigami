# app.py

from aiohttp import web

from aiohttp_apigami import OpenApiVersion, setup_apispec_aiohttp, validation_middleware
from aiohttp_apigami.swagger_ui import LayoutOption

from .routes import setup_routes


def create_app() -> web.Application:
    app = web.Application()
    setup_routes(app)

    # In real life, you should use a database
    app["users"] = {}

    setup_apispec_aiohttp(
        app,
        title="User API",
        version="0.0.1",
        swagger_path="/api/docs",
        swagger_layout=LayoutOption.Standalone,
        openapi_version=OpenApiVersion.V20,
    )
    app.middlewares.append(validation_middleware)

    return app


if __name__ == "__main__":
    web_app = create_app()
    web.run_app(web_app)
