from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
if TYPE_CHECKING:
    # Absolutely horrendous type checking hacks. Does not work anyways.
    # TODO: remove with SQLAlchemy.
    from dataclasses import dataclass as fake_dataclass

    class Query:
        filter_by: "Query"

        def __init__(self) -> None:
            ...

        def __call__(self, **kwargs: Any) -> "Query":
            ...

        def first(self) -> Any:
            ...

        def all(self) -> list[Any]:
            ...

    @fake_dataclass
    class _Model:
        query: Query = Query()
        __table__: Any = None

    Model = _Model
else:
    Model = db.Model
    fake_dataclass = lambda x: x


@fake_dataclass
class User(Model):
    id: int = db.Column(db.Integer, primary_key=True)
    username: str = db.Column(db.Text, unique=True)
    password: str = db.Column(db.Text)  # argon2 hash


@fake_dataclass
class Form(Model):
    id: int = db.Column(db.Integer, primary_key=True)
    schema: str = db.Column(db.Text)
    created_at: Any = db.Column(db.DateTime)
    creator_id: int = db.Column(db.Integer, db.ForeignKey(User.id))
    access_control_flags: int = db.Column(db.Integer, nullable=False, default=0)

    creator: User = db.relationship("User", foreign_keys="Form.creator_id")


@dataclass
class Field:
    name: str  # max 256 bytes


@dataclass
class InfoField:
    text: str # max 512 characters


@dataclass
class TextField(Field):
    default: str  # max 1023 bytes


@dataclass
class ChoiceField(Field):
    single: bool
    default: int
    choices: list[str]  # max 64 elements with 64 length


@dataclass
class RangeField(Field):
    default: int
    min: int
    max: int
