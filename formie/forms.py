from flask import render_template, Blueprint

bp = Blueprint("forms", __name__, url_prefix="/forms")


@bp.route("/new", methods=("GET", "POST"))
def new_form():
    return render_template("forms/new.html")
