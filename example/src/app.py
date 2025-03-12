# app.py

from aiohttp import web

from apispec_aiohttp import setup_apispec_aiohttp, validation_middleware

from .routes import setup_routes


def create_app() -> web.Application:
    app = web.Application()
    setup_routes(app)

    # In real life, you should use a database
    app["users"] = {}

    setup_apispec_aiohttp(app, swagger_path="/api/docs")
    app.middlewares.append(validation_middleware)

    return app


if __name__ == "__main__":
    web_app = create_app()
    web.run_app(web_app)
