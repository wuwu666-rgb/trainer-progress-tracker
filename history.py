from flask import Blueprint, g, render_template

from clients import get_visible_client

bp = Blueprint("history", __name__)


def get_workouts(client_id):
    return g.db.execute(
        "SELECT id, workout_date, exercise, reps, weight_lb, "
        "NULL AS duration_min, NULL AS distance_km FROM workouts WHERE client_id = ? "
        "UNION ALL "
        "SELECT id, workout_date, exercise, NULL, NULL, duration_min, distance_km "
        "FROM cardio_workouts WHERE client_id = ? "
        "ORDER BY workout_date DESC, id DESC",
        (client_id, client_id),
    ).fetchall()


@bp.get("/clients/<int:client_id>/history")
def index(client_id):
    client = get_visible_client(client_id)
    return render_template("history.html", client=client, workouts=get_workouts(client_id))
