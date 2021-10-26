import os

from flask import render_template, Flask

from formie import auth, forms, models


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_pyfile("config.py", silent=True)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test.db"
    app.config["SECRET_KEY"] = "secret tunnell"
    models.db.init_app(app)

    app.register_blueprint(auth.bp)
    app.register_blueprint(forms.bp)

    @app.route("/")
    def index():
        return render_template("index.html")

    return app
