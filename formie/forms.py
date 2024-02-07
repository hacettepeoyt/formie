import csv
import datetime
import io
import json
from collections import defaultdict
from dataclasses import dataclass
from enum import Flag
from typing import cast, Type, TYPE_CHECKING, Union

from flask import (
    abort,
    g,
    redirect,
    render_template,
    request,
    url_for,
    Blueprint,
    Response,
)

if TYPE_CHECKING:
    from flask.typing import ResponseReturnValue
else:
    ResponseReturnValue = "ResponseReturnValue"

from formie import auth
from formie.models import (
    db,
    Field,
    ChoiceField,
    Form,
    InfoField,
    Model,
    TextField,
    RangeField,
)

bp = Blueprint("forms", __name__, url_prefix="/forms")


JSONData = Union[str, int, bool, float, list["JSONData"], dict[str, "JSONData"]]


class ACF(Flag):
    """Access control flags for forms. Can be used to limit viewing results/answering for other users."""

    HIDE_RESULTS = 0x1
    DISALLOW_ANON_ANSWER = 0x2


def validate_schema(data: JSONData) -> str:
    """Validates the given schema. Returns a string with the error on fail."""
    if not isinstance(data, list):
        return "Invalid schema root type."

    if len(data) == 0:
        # Disallow empty schemas.
        return "Cannot make an empty form."

    if len(data) > 64:
        return f"Cannot have more than 64 fields."

    for i, field in enumerate(data):
        if not isinstance(field, dict):
            return f"Invalid type for field #{i}"

        if TYPE_CHECKING:
            field = cast(dict[str, JSONData], field)

        if "type" not in field:
            return f"Field #{i} needs a type."

        if field["type"] == "info":
            if "text" not in field:
                return f"Field #{i} needs information text."

            if len(field) != 2:
                return f"Field #{i} cannot have more than 2 attributes."

            if not isinstance(field["text"], str):
                return f"Field #{i} has invalid text type."

            if len(field["text"]) > 512:
                return f"Field #{i}'s information text cannot have more than 512 characters."

            continue

        if (
            "name" not in field
            or not isinstance(field["name"], str)
            or len(field["name"]) == 0
        ):
            return f"Field #{i} requires a question."

        if len(field["name"]) > 256:
            return f"Field #{i}'s question cannot be longer than 256 characters."

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
                    return (
                        f"Field #{i} choice #{ci} cannot have more than 64 characters."
                    )

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


def validate_answer(schema: list[Field], form: dict[str, str]) -> str:
    """Validates an answer against the given schema. Returns an error string on failure."""

    for i, field in enumerate(schema):
        if isinstance(field, InfoField):
            continue

        if not isinstance(field, ChoiceField) or field.single:
            if f"col{i}" not in form:
                return f"Question #{i + 1} is missing an answer."

            if isinstance(field, TextField) and len(form[f"col{i}"]) > 1023:
                return (
                    f"Question #{i + 1}'s answer cannot be longer than 1023 characters."
                )
            elif isinstance(field, (ChoiceField, RangeField)):
                # log10(2 ** 64) ~= 19 so 20 characters should be more than enough.
                if len(form[f"col{i}"]) > 20:
                    return f"Question #{i + 1} answer is out of bounds."

                try:
                    answer = int(form[f"col{i}"])
                except ValueError:
                    return f"Question #{i + 1} has an invalid answer."

                if isinstance(field, ChoiceField) and answer >= len(field.choices):
                    return f"Question #{i + 1} has an invalid answer."
                elif isinstance(field, RangeField) and (
                    answer < field.min or answer > field.max
                ):
                    return f"Question #{i + 1}'s answer is out of bounds."
        else:
            if f"col{i}" in form:
                try:
                    answer = int(answer)
                except ValueError:
                    return f"Question #{i + 1} has an invalid answer."
            else:
                answer = 0
                for part in form:
                    try:
                        if part.startswith(f"col{i}"):
                            answer |= 1 << int(part.split("_")[1])
                    except ValueError:
                        pass

            if answer < 0 or answer >= (1 << len(field.choices)):
                return f"Question #{i + 1}'s answer is out of bounds."

    return ""


def decode_fields(data: list[dict[str, JSONData]]) -> list[Field]:
    fields: list[Field] = []
    for elem in data:
        assert isinstance(elem["type"], str)

        if elem["type"] == "text":
            del elem["type"]

            assert isinstance(elem["default"], str)

            fields.append(TextField(name=elem["name"], default=elem["default"]))

            elem["type"] = "text"
        elif elem["type"] == "choice":
            del elem["type"]

            assert isinstance(elem["single"], bool)
            assert isinstance(elem["default"], int)
            assert isinstance(elem["choices"], list)

            fields.append(ChoiceField(name=elem["name"], single=elem["single"], default=elem["default"], choices=elem["choices"]))  # type: ignore[arg-type]
            elem["type"] = "choice"
        elif elem["type"] == "range":
            del elem["type"]

            assert isinstance(elem["default"], int)
            assert isinstance(elem["min"], int)
            assert isinstance(elem["max"], int)

            fields.append(
                RangeField(
                    name=elem["name"],
                    default=elem["default"],
                    min=elem["min"],
                    max=elem["max"],
                )
            )
            elem["type"] = "range"
        elif elem["type"] == "info":
            assert isinstance(elem["text"], str)

            fields.append(InfoField(text=elem["text"]))

    return fields


MODELS: dict[str, Type[Model]] = {}


def create_model(name: str, fields: list[Field]) -> Type[Model]:
    if name in MODELS:
        return MODELS[name]

    cols = {"id": db.Column(db.Integer, primary_key=True)}
    for i, field in enumerate(fields):
        if isinstance(field, InfoField):
            continue

        if isinstance(field, TextField):
            col = db.Column(db.Text, default=field.default)
        elif isinstance(field, ChoiceField):
            col = db.Column(db.Integer, default=field.default)
        elif isinstance(field, RangeField):
            col = db.Column(db.Integer, default=field.default)
        cols[f"col{i}"] = col
    cls = type(name, (db.Model,), cols)  # type: ignore[arg-type]
    MODELS[name] = cls
    return cls


@bp.route("/")
def all_forms() -> ResponseReturnValue:
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
def new_form() -> ResponseReturnValue:
    if request.method == "POST":
        acf: ACF = ACF(0)
        if request.args.get("hide_results", "false") == "true":
            acf |= ACF.HIDE_RESULTS
        if request.args.get("disallow_anon_answer", "false") == "true":
            acf |= ACF.DISALLOW_ANON_ANSWER

        schema = request.json
        if schema is None:
            return "A JSON Body is required", 400

        error = validate_schema(cast(JSONData, schema))

        if error:
            return error, 400

        try:
            schema_str = json.dumps(schema)  # TODO: fetch original instead
            fields = decode_fields(cast(list[dict[str, JSONData]], schema))
            form = Form(
                schema=schema_str,
                created_at=datetime.datetime.now(),
                creator_id=g.user.id,
                access_control_flags=acf.value,
            )
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
def form(form_id: int) -> ResponseReturnValue:
    form = Form.query.filter_by(id=form_id).first()
    if form is None:
        abort(404)
    schema = json.loads(form.schema)

    model = create_model(str(form.id), decode_fields(schema.copy()))

    if request.method == "POST":
        if (
            ACF.DISALLOW_ANON_ANSWER in ACF(form.access_control_flags)
            and g.user is None
        ):
            abort(403)  # TODO: Better pages for aborts

        error = validate_answer(decode_fields(schema), request.form)
        if error:
            return error, 400

        values: dict[str, Union[int, str]] = defaultdict(int)
        for key in request.form:
            try:
                if not key.startswith("col"):
                    continue

                parts = key.split("_")
                key = parts[0]

                idx = int(key.lstrip("col"))
                if idx >= len(schema):
                    continue

                if len(parts) == 2:
                    key = parts[0]
                    assert isinstance(values[key], int)
                    values[key] = cast(int, values[key]) | (1 << int(parts[1]))
                else:
                    values[key] = request.form[key]
            except ValueError:
                pass

        db.session.add(model(**values))  # type: ignore[arg-type]
        db.session.commit()

        if url := request.args.get("goto", None):
            return redirect(url)

        can_view_results: bool = ACF.HIDE_RESULTS not in ACF(
            form.access_control_flags
        ) or (g.user is not None and g.user.id == form.creator_id)
        results_url: str = url_for("forms.view_results", form_id=form_id)

        return render_template(
            "forms/submission_successful.html",
            can_view_results=can_view_results,
            results_url=results_url,
        )

    schema = list(enumerate(schema))
    for i, field in schema:
        if field["type"] == "choice":
            schema[i][1]["choices"] = list(enumerate(schema[i][1]["choices"]))

    return render_template("forms/form.html", schema=schema)


@bp.route("/<int:form_id>/results")
def view_results(form_id: int) -> ResponseReturnValue:
    form = Form.query.filter_by(id=form_id).first()
    if form is None:
        abort(404)

    if ACF.HIDE_RESULTS in ACF(form.access_control_flags) and (
        g.user is None or g.user.id != form.creator_id
    ):
        abort(403)

    schema = json.loads(form.schema)
    fields = decode_fields(schema)
    model = create_model(str(form.id), fields)
    results = []
    for res in model.query.all():
        cols = [res.id]
        for i, field in enumerate(fields):
            if isinstance(field, InfoField):
                continue

            if not isinstance(field, ChoiceField):
                cols.append(getattr(res, f"col{i}"))
            else:
                if field.single:
                    cols.append(field.choices[int(getattr(res, f"col{i}"))])
                else:
                    answer_flag: int = int(getattr(res, f"col{i}"))
                    answer: list[str] = []
                    for choice_index, choice in enumerate(field.choices):
                        if answer_flag & (1 << choice_index):
                            answer.append(choice)
                    cols.append("+".join(answer))
        results.append(cols)

    if request.args.get("format", default=None, type=str) == "csv":
        buf = io.StringIO()
        csv.writer(buf).writerows(results)
        buf.seek(0)
        return cast(Union[Response, str], Response(buf.read(), mimetype="text/csv"))

    return render_template("forms/results.html", schema=schema, results=results)
