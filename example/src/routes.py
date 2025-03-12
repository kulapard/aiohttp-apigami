# routes.py
from aiohttp import web

from .views import create_user, get_user, get_users


def setup_routes(app: web.Application) -> None:
    app.router.add_post("/users", create_user)
    app.router.add_get("/users", get_users)
    app.router.add_get("/users/{id}", get_user)
