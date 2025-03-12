# schemas.py
from marshmallow import Schema, fields, validate


class User(Schema):
    id = fields.Integer(required=True)
    name = fields.String(required=True)
    gender = fields.String(validate=validate.OneOf(["f", "m"]))


class Message(Schema):
    message = fields.String()


class UsersList(Schema):
    users = fields.Nested(User(many=True))


class GetUser(Schema):
    id = fields.Integer(required=True)
