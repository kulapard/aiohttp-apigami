from dataclasses import dataclass

from .typedefs import HandlerType


@dataclass(frozen=True, slots=True, kw_only=True)
class RouteData:
    method: str
    path: str
    handler: HandlerType
