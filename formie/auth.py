from flask import render_template, Blueprint

bp = Blueprint("auth", __name__, url_prefix="/auth")
