import datetime
import json
from dataclasses import dataclass
from typing import List

from flask import abort, g, redirect, render_template, request, url_for, Blueprint

from formie import auth
from formie.models import db, Field, ChoiceField, Form, TextField, RangeField

bp = Blueprint("forms", __name__, url_prefix="/forms")


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

        error = None
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

        return render_template("forms/creation_successful.html")
    return render_template("forms/new.html")


@bp.route("/<int:form_id>", methods=("GET", "POST"))
def form(form_id: int):
    form = Form.query.filter_by(id=form_id).first()
    if form is None:
        abort(404)
    schema = json.loads(form.schema)

    model = create_model(str(form.id), decode_fields(schema.copy()))

    if request.method == "POST":
        db.session.add(model(**request.form))
        db.session.commit()
        return redirect(url_for("forms.view_results", form_id=form_id))

    return render_template("forms/form.html", schema=enumerate(schema), s2=enumerate(schema))


@bp.route("/<int:form_id>/results")
def view_results(form_id: int):
    form = Form.query.filter_by(id=form_id).first()
    if form is None:
        abort(404)

    schema = json.loads(form.schema)
    model = create_model(str(form.id), decode_fields(schema))
    results = []
    for res in model.query.all():
        cols = []
        for col in model.__table__.columns.keys():
            cols.append(getattr(res, col))
        results.append(cols)

    return render_template(
        "forms/results.html", schema=schema, results=results
    )
