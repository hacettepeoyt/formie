import os

from flask import render_template, Flask

from formie import auth, forms


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_pyfile("config.py", silent=True)

    app.register_blueprint(auth.bp)
    app.register_blueprint(forms.bp)

    @app.route("/")
    def index():
        return render_template("index.html")

    return app
