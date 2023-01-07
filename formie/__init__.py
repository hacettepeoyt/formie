import os
from typing import TYPE_CHECKING

import sqlalchemy
from flask import redirect, render_template, url_for, Flask

from formie import auth, forms, models

if TYPE_CHECKING:
    from flask.typing import ResponseReturnValue
else:
    ResponseReturnValue = "ResponseReturnValue"


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["SQLALCHEMY_DATABASE_URI"]
    app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
    models.db.init_app(app)  # type: ignore[no-untyped-call]

    app.register_blueprint(auth.bp)
    app.register_blueprint(forms.bp)

    if app.config["ENV"] == "production":
        from werkzeug.middleware.proxy_fix import ProxyFix

        app.wsgi_app = ProxyFix(  # type: ignore[assignment]
            app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
        )

    with app.app_context():
        try:
            models.Form.query.all()
        except sqlalchemy.exc.OperationalError:
            models.db.create_all()

    @app.route("/")
    def index() -> ResponseReturnValue:
        return redirect(url_for("forms.all_forms"))  # render_template("index.html")

    return app
