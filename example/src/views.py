# views.py
from aiohttp import web

from apispec_aiohttp import docs
from apispec_aiohttp.decorators.request import json_schema, match_info_schema
from apispec_aiohttp.decorators.response import response_schema

from .schemas import GetUser, Message, User, UsersList


@docs(
    tags=["users"],
    summary="Get users list",
    description="Get list of all users from our toy database",
    responses={
        200: {"description": "Ok. Users list", "schema": UsersList},
        404: {"description": "Not Found"},
        500: {"description": "Server error"},
    },
)
async def get_users(request: web.Request) -> web.Response:
    return web.json_response({"users": request.app["users"]})


@docs(
    tags=["users"],
    summary="Create new user",
    description="Add new user to our toy database",
    responses={
        200: {"description": "Ok. User created", "schema": Message},
        401: {"description": "Unauthorized"},
        409: {"description": "User already exists"},
        422: {"description": "Validation error"},
        500: {"description": "Server error"},
    },
)
@json_schema(User)
@response_schema(Message)
async def create_user(request: web.Request) -> web.Response:
    new_user = request["json"]
    user_id = new_user["id"]
    if user_id in request.app["users"]:
        return web.json_response(status=409)
    request.app["users"][user_id] = new_user
    return web.json_response({"message": f"Hello {new_user['name']}!"})


@docs(
    tags=["users"],
    summary="Get user by id",
    description="Get user by id from our toy database",
    responses={
        200: {"description": "Ok", "schema": User},
        401: {"description": "Unauthorized"},
        422: {"description": "Validation error"},
        500: {"description": "Server error"},
    },
)
@match_info_schema(GetUser)
@response_schema(User)
async def get_user(request: web.Request) -> web.Response:
    user_id = request["match_info"]["id"]
    if user_id not in request.app["users"]:
        return web.json_response(status=404)
    user = request.app["users"][user_id]
    return web.json_response(user)
