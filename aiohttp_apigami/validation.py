from dataclasses import dataclass

import marshmallow as m


@dataclass
class ValidationSchema:
    schema: m.Schema
    location: str
    put_into: str | None = None
