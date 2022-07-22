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

    if app.config["ENV"] == "production":
        from werkzeug.middleware.proxy_fix import ProxyFix

        app.wsgi_app = ProxyFix(
            app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
        )


    @app.route("/")
    def index():
        return redirect(url_for("forms.all_forms")) # render_template("index.html")

    return app
