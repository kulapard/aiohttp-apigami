from string import Formatter
from typing import Any

from aiohttp import web


def get_path(route: web.AbstractRoute) -> str | None:
    if route.resource is None:
        return None
    path_info = route.resource.get_info()
    return path_info.get("path") or path_info.get("formatter")


def get_path_keys(path: str) -> list[str]:
    return [i[1] for i in Formatter().parse(path) if i[1]]


def issubclass_py37fix(cls: Any, cls_info: Any) -> bool:
    try:
        return issubclass(cls, cls_info)
    except TypeError:
        return False
