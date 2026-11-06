from decimal import Decimal

from flask import Blueprint, g, render_template

from clients import get_visible_client

bp = Blueprint("history", __name__)


def get_workouts(client_id):
    rows = g.db.execute(
        "SELECT id, workout_date, exercise, reps, weight_lb, set_count, "
        "NULL AS duration_min, NULL AS distance_km FROM workouts WHERE client_id = ? "
        "UNION ALL "
        "SELECT id, workout_date, exercise, NULL, NULL, set_count, duration_min, distance_km "
        "FROM cardio_workouts WHERE client_id = ? "
        "ORDER BY workout_date DESC, id DESC",
        (client_id, client_id),
    ).fetchall()
    return [
        dict(row, no_added_weight=row["weight_lb"] is not None and Decimal(row["weight_lb"]).is_zero())
        for row in rows
    ]


@bp.get("/clients/<int:client_id>/history")
def index(client_id):
    client = get_visible_client(client_id)
    return render_template("history.html", client=client, workouts=get_workouts(client_id))
