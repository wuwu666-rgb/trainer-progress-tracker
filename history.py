from decimal import Decimal

from flask import Blueprint, abort, g, redirect, render_template, request, url_for

from auth import check_csrf
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
    return [workout_display(row) for row in rows]


def workout_display(row):
    workout = dict(row)
    workout.setdefault("duration_min", None)
    weight = workout.get("weight_lb")
    workout["no_added_weight"] = weight is None or Decimal(weight).is_zero()
    return workout


@bp.get("/clients/<int:client_id>/history")
def index(client_id):
    client = get_visible_client(client_id)
    return render_template("history.html", client=client, workouts=get_workouts(client_id))


@bp.route("/clients/<int:client_id>/history/<kind>/<int:record_id>/delete", methods=["GET", "POST"])
def delete_record(client_id, kind, record_id):
    if g.user["role"] != "trainer":
        abort(403)
    table = {"strength": "workouts", "timed": "cardio_workouts"}.get(kind)
    if table is None:
        abort(404)

    client = get_visible_client(client_id)
    query = request.args.get("q") or None
    if request.method == "POST":
        check_csrf()
        with g.db:
            deleted = g.db.execute(
                f"DELETE FROM {table} WHERE id = ? AND client_id = ?",
                (record_id, client_id),
            )
            if not deleted.rowcount:
                abort(404)
        return redirect(url_for("history.index", client_id=client_id, q=query))

    row = g.db.execute(
        f"SELECT * FROM {table} WHERE id = ? AND client_id = ?",
        (record_id, client_id),
    ).fetchone()
    if row is None:
        abort(404)
    return render_template("history_delete.html", client=client, workout=workout_display(row))
