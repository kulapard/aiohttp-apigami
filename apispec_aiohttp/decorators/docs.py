from collections.abc import Callable
from typing import Any, TypeVar

from apispec_aiohttp.typedefs import HandlerType

T = TypeVar("T", bound=HandlerType)


def docs(**kwargs: Any) -> Callable[[T], T]:
    """
    Annotate the decorated view function with the specified Swagger
    attributes.

    Usage:

    .. code-block:: python

        from aiohttp import web

        @docs(tags=['my_tag'],
              summary='Test method summary',
              description='Test method description',
              parameters=[{
                      'in': 'header',
                      'name': 'X-Request-ID',
                      'schema': {'type': 'string', 'format': 'uuid'},
                      'required': 'true'
                  }]
              )
        async def index(request):
            return web.json_response({'msg': 'done', 'data': {}})

    """

    def wrapper(func: T) -> T:
        if not kwargs.get("produces"):
            kwargs["produces"] = ["application/json"]
        if not hasattr(func, "__apispec__"):
            func.__apispec__ = {"schemas": [], "responses": {}, "parameters": []}  # type: ignore
            func.__schemas__ = []  # type: ignore
        extra_parameters = kwargs.pop("parameters", [])
        extra_responses = kwargs.pop("responses", {})
        func.__apispec__["parameters"].extend(extra_parameters)  # type: ignore
        func.__apispec__["responses"].update(extra_responses)  # type: ignore
        func.__apispec__.update(kwargs)  # type: ignore
        return func

    return wrapper
