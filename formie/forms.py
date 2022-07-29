import csv
import datetime
import io
import json
from dataclasses import dataclass
from enum import Flag
from typing import List

from flask import abort, g, redirect, render_template, request, url_for, Blueprint, Response

from formie import auth
from formie.models import db, Field, ChoiceField, Form, TextField, RangeField

bp = Blueprint("forms", __name__, url_prefix="/forms")


class ACF(Flag):
    """ Access control flags for forms. Can be used to limit viewing results/answering for other users. """
    HIDE_RESULTS = 0x1
    DISALLOW_ANON_ANSWER = 0x2


def validate_schema(data: list) -> str:
    """ Validates the given schema. Returns a string with the error on fail. """
    if len(data) == 0:
        # Disallow empty schemas.
        return "Cannot make an empty form."

    if not isinstance(data, list):
        return "Invalid schema root type."

    if len(data) > 64:
        return f"Cannot have more than 64 fields."

    for i, field in enumerate(data):
        if not isinstance(field, dict):
            return f"Invalid type for field #{i}"

        if "name" not in field or len(field["name"]) == 0:
            return f"Field #{i} requires a question."

        if len(field["name"]) > 256:
            return f"Field #{i}'s question cannot be longer than 256 characters."

        if "type" not in field:
            return f"Field #{i} needs a type."

        if field["type"] == "text":
            if "default" not in field:
                return f"Field #{i} needs a default attribute."

            if not isinstance(field["default"], str):
                return f"Field #{i}'s default must be a string."

            if len(field["default"]) > 1023:
                return f"Field #{i}'s default cannot be longer than 1023 characters."

            if len(field) != 3:
                return f"Field #{i} cannot have more than 3 attributes."
        elif field["type"] == "choice":
            if "default" not in field:
                return f"Field #{i} needs a default attribute."

            if not isinstance(field["default"], int):
                return f"Field #{i}'s default must be an integer."

            if "single" not in field:
                return f"Field #{i} needs a single attribute."

            if not isinstance(field["single"], bool):
                return f"Field #{i}'s single must be a boolean."

            if "choices" not in field:
                return f"Field #{i} needs a choices attribute"

            if not isinstance(field["choices"], list):
                return f"Field #{i}'s choices must be a list."

            if len(field["choices"]) > 64:
                return f"Field #{i} cannot have more than 64 choices."

            if len(field["choices"]) == 0:
                return f"Field #{i} needs at least one choice."

            for ci, choice in enumerate(field["choices"]):
                if not isinstance(choice, str):
                    return f"Field #{i} choice #{ci} must be a string."

                if len(choice) > 64:
                    return f"Field #{i} choice #{ci} cannot have more than 64 characters."

            if len(field) != 5:
                return f"Field #{i} cannot have more than 5 attributes."
        elif field["type"] == "range":
            for attr in ("default", "min", "max"):
                if attr not in field:
                    return f"Field #{i} needs a {attr} attribute."

                if not isinstance(field[attr], int):
                    return f"Field #{i} must be an integer."

            if field["default"] < field["min"]:
                return f"Field #{i}'s default cannot be lower than minimum."

            if field["default"] > field["max"]:
                return f"Field #{i}'s default cannot be higher than maximum."

            if len(field) != 5:
                return f"Field #{i} cannot have more than 5 attributes."
        else:
            return f"Field #{i} has an invalid type."

    return ""


def decode_fields(data: dict) -> List[Field]:
    fields: List[Field] = []
    for elem in data:
        if "name" not in elem:
            raise ValueError("invalid format")
        if len(elem["name"]) > 256:
            raise ValueError("invalid value")

        if elem["type"] == "text":
            del elem["type"]
            if len(elem) != 2:
                raise ValueError("invalid format")
            if len(elem["default"]) > 1024:
                raise ValueError("invalid value")

            fields.append(TextField(**elem))
            elem["type"] = "text"
        elif elem["type"] == "choice":
            del elem["type"]

            fields.append(ChoiceField(**elem))
            elem["type"] = "choice"
        elif elem["type"] == "range":
            del elem["type"]
            fields.append(RangeField(**elem))
            elem["type"] = "range"
        else:
            raise ValueError("invalid format")
    return fields


MODELS = {}

def create_model(name: str, fields: List[Field]):
    if name in MODELS:
        return MODELS[name]

    cols = {"id": db.Column(db.Integer, primary_key=True)}
    for i, field in enumerate(fields):
        if isinstance(field, TextField):
            col = db.Column(db.Text, default=field.default)
        elif isinstance(field, ChoiceField):
            col = db.Column(db.Integer, default=field.default)
        elif isinstance(field, RangeField):
            col = db.Column(db.Integer, default=field.default)
        cols[f"col{i}"] = col
    cls = type(name, (db.Model,), cols)
    MODELS[name] = cls
    return cls


@bp.route("/")
def all_forms():
    forms = []
    for form in Form.query.all():
        form_dict = {}
        form_dict["id"] = form.id
        form_dict["creator"] = "anon"
        if form.creator:
            form_dict["creator"] = form.creator.username
        forms.append(form_dict)
    return render_template("forms/forms.html", forms=forms)


@bp.route("/new", methods=("GET", "POST"))
@auth.login_required
def new_form():
    if request.method == "POST":
        schema = request.json
        error = validate_schema(schema)

        if error:
            return error, 400

        try:
            schema_str = json.dumps(schema)  # TODO: fetch original instead
            fields = decode_fields(schema)
            form = Form(schema=schema_str, created_at=datetime.datetime.now(), creator_id=g.user.id)
            db.session.add(form)
            db.session.commit()
            create_model(str(form.id), fields).__table__.create(db.engine)
        except Exception as e:
            raise e
            abort(401)
        db.session.commit()

        return url_for("forms.form", form_id=form.id), 200
    return render_template("forms/new.html")


@bp.route("/<int:form_id>", methods=("GET", "POST"))
def form(form_id: int):
    form = Form.query.filter_by(id=form_id).first()
    if form is None:
        abort(404)
    schema = json.loads(form.schema)

    model = create_model(str(form.id), decode_fields(schema.copy()))

    if request.method == "POST":
        if ACF.DISALLOW_ANON_ANSWER in ACF(form.access_control_flags) and g.user is None:
            abort(403)  # TODO: Better pages for aborts

        db.session.add(model(**request.form))
        db.session.commit()
        return redirect(url_for("forms.view_results", form_id=form_id))

    return render_template("forms/form.html", schema=enumerate(schema))


@bp.route("/<int:form_id>/results")
def view_results(form_id: int):
    form = Form.query.filter_by(id=form_id).first()
    if form is None:
        abort(404)

    if ACF.HIDE_RESULTS in ACF(form.access_control_flags) and (g.user is None or g.user.id != form.creator_id):
        abort(403)

    schema = json.loads(form.schema)
    model = create_model(str(form.id), decode_fields(schema))
    results = []
    for res in model.query.all():
        cols = []
        for col in model.__table__.columns.keys():
            cols.append(getattr(res, col))
        results.append(cols)

    if request.args.get('format', default = None, type=str) == "csv":
        buf = io.StringIO()
        csv.writer(buf).writerows(results)
        buf.seek(0)
        return Response(buf.read(), mimetype='text/csv')

    return render_template(
        "forms/results.html", schema=schema, results=results
    )
