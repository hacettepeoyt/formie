import functools
from typing import Any, Callable

from flask import (
    g,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
    Blueprint,
)
from flask.typing import ResponseReturnValue
from passlib.hash import argon2
from sqlalchemy.exc import IntegrityError

from formie.models import db, User

bp = Blueprint("auth", __name__, url_prefix="/auth")


def login_required(view: Callable[..., ResponseReturnValue]) -> Callable[..., ResponseReturnValue]:
    """View decorator that redirects anonymous users to the login page."""

    @functools.wraps(view)
    def wrapped_view(**kwargs: Any) -> ResponseReturnValue:
        if g.user is None:
            return redirect(url_for("auth.login"))

        return view(**kwargs)

    return wrapped_view


@bp.before_app_request
def load_logged_in_user() -> None:
    """If a user id is stored in the session, load the user object from
    the database into ``g.user``."""
    user_id = session.get("user_id")

    if user_id is None:
        g.user = None
    else:
        g.user = User.query.filter_by(id=user_id).first()


@bp.route("/register", methods=("GET", "POST"))
def register() -> ResponseReturnValue:
    """Register a new user.
    Validates that the username is not already taken. Hashes the
    password for security.
    """
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        error = None

        if not username:
            error = "An username is required."
        elif not password:
            error = "A password is required."
        elif len(username) > 32:
            error = "Username cannot be longer than 32 characters."
        elif len(password) > 256:
            error = "Password cannot be longer than 256 characters."

        if error is None:
            try:
                db.session.add(User(username=username, password=argon2.hash(password))) # type: ignore[no-untyped-call]
                db.session.commit()

                return redirect(url_for("auth.login"))
            except IntegrityError:
                error = "Username is already in use."

        flash(error)

    return render_template("auth/register.html")


@bp.route("/login", methods=("GET", "POST"))
def login() -> ResponseReturnValue:
    """Log in a registered user by adding the user id to the session."""
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        error = None
        user = User.query.filter_by(username=username).first()

        if user is None or not argon2.verify(password, user.password): # type: ignore[no-untyped-call]
            error = "Incorrect username/password."

        if error is None:
            # store the user id in a new session and return to the index
            session.clear()
            session["user_id"] = user.id
            return redirect(url_for("index"))

        flash(error)

    return render_template("auth/login.html")


@bp.route("/logout")
def logout() -> ResponseReturnValue:
    """Clear the current session, including the stored user id."""
    session.clear()
    return redirect(url_for("index"))
