from flask import Blueprint, render_template

bp = Blueprint("planning", __name__)


@bp.get("/planning")
def index():
    return render_template("planning.html")
