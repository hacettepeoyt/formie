from dataclasses import dataclass
from typing import List

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.Text, unique=True)
    password = db.Column(db.Text)  # argon2 hash


class Form(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    schema = db.Column(db.Text)
    created_at = db.Column(db.DateTime)
    creator_id = db.Column(db.Integer, db.ForeignKey(User.id))

    creator = db.relationship('User', foreign_keys='Form.creator_id')


@dataclass
class Field:
    name: str  # max 256 bytes


@dataclass
class TextField(Field):
    default: str  # max 1024 bytes


@dataclass
class ChoiceField(Field):
    single: bool
    default: int
    choices: List[str]  # max 64 if single is false

@dataclass
class NumberSliderField(Field):
   default: int
   min: int
   max: int
