from dataclasses import dataclass, field
from typing import Any

from marshmallow import EXCLUDE, Schema, fields


class HeaderSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    some_header = fields.String()


class MatchInfoSchema(Schema):
    uuid = fields.Integer()


class CookiesSchema(Schema):
    some_cookie = fields.String()


class MyNestedSchema(Schema):
    i = fields.Int()


class RequestSchema(Schema):
    id = fields.Int()
    name = fields.Str(metadata={"description": "name"})
    bool_field = fields.Bool()
    list_field = fields.List(fields.Int())
    nested_field = fields.Nested(MyNestedSchema)


class ResponseSchema(Schema):
    msg = fields.Str()
    data = fields.Dict()


@dataclass
class NestedDataclass:
    i: int


@dataclass
class RequestDataclass:
    id: int
    name: str
    bool_field: bool
    list_field: list[int]
    nested_field: NestedDataclass | None = None


@dataclass
class ResponseDataclass:
    msg: str
    data: dict[str, Any] = field(default_factory=dict)


class MyException(Exception):
    def __init__(self, message: dict[str, Any]) -> None:
        self.message = message
