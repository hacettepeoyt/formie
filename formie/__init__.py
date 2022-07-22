import os

from flask import redirect, render_template, url_for, Flask

from formie import auth, forms, models


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["SQLALCHEMY_DATABASE_URI"]
    app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
    models.db.init_app(app)

    app.register_blueprint(auth.bp)
    app.register_blueprint(forms.bp)

    @app.route("/")
    def index():
        return redirect(url_for("forms.all_forms")) # render_template("index.html")

    return app
