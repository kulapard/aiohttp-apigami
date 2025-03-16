# routes.py
from aiohttp import web

from .views import UserView, create_user, get_users


def setup_routes(app: web.Application) -> None:
    # function-based routes
    app.router.add_post("/users", create_user)
    app.router.add_get("/users", get_users)
    # class-based routes
    app.router.add_view("/users/{id}", UserView)
