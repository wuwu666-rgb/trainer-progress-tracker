from flask import Blueprint, abort, g, render_template

bp = Blueprint("history", __name__)


@bp.get("/clients/<int:client_id>/history")
def index(client_id):
    client = g.db.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
    if client is None:
        abort(404)
    workouts = g.db.execute(
        "SELECT * FROM workouts WHERE client_id = ? ORDER BY workout_date DESC, id DESC",
        (client_id,),
    ).fetchall()
    return render_template("history.html", client=client, workouts=workouts)
