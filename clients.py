from flask import Blueprint, g, render_template

bp = Blueprint("clients", __name__)


@bp.get("/clients")
def index():
    clients = g.db.execute("SELECT id, name FROM clients ORDER BY name").fetchall()
    return render_template("clients.html", clients=clients)
