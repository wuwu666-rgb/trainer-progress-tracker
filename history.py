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
    sessions = g.db.execute(
        """
        WITH recorded_sets AS (
            SELECT w.id, w.workout_date, w.plan_name, w.recorder_id, e.id AS exercise_id,
                   recorder.name AS recorder_name, recorder.role AS recorder_role,
                   e.name, e.unit, s.result, s.weight_lb,
                   ROW_NUMBER() OVER (PARTITION BY w.id ORDER BY e.position, s.position) AS set_order
            FROM workout_sessions AS w
            JOIN workout_session_exercises AS e ON e.workout_id = w.id
            JOIN workout_session_sets AS s ON s.exercise_id = e.id
            LEFT JOIN users AS recorder ON recorder.id = w.recorder_id
            WHERE w.client_id = ? AND w.completed_at IS NOT NULL
        )
        SELECT id, workout_date, plan_name, recorder_id, recorder_name, recorder_role,
               COUNT(DISTINCT exercise_id) AS exercise_count, COUNT(*) AS set_count,
               MAX(CASE WHEN set_order = 1 THEN name END) AS preview_exercise,
               MAX(CASE WHEN set_order = 1 THEN unit END) AS preview_unit,
               MAX(CASE WHEN set_order = 1 THEN result END) AS preview_result,
               MAX(CASE WHEN set_order = 1 THEN weight_lb END) AS preview_weight
        FROM recorded_sets
        GROUP BY id, workout_date, plan_name, recorder_id, recorder_name, recorder_role
        """,
        (client_id,),
    )
    workouts = [workout_display(row) for row in rows]
    workouts.extend(dict(row, grouped=True) for row in sessions)
    return sorted(workouts, key=lambda item: (item["workout_date"], item["id"]), reverse=True)


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
    table = {"strength": "workouts", "timed": "cardio_workouts", "session": "workout_sessions"}.get(kind)
    if table is None:
        abort(404)

    client = get_visible_client(client_id)
    query = request.args.get("q") or None
    grouped = kind == "session"
    condition = "id = ? AND client_id = ?"
    params = (record_id, client_id)
    if grouped:
        condition += " AND recorder_id = ? AND completed_at IS NOT NULL"
        params += (g.user["id"],)
    if request.method == "POST":
        check_csrf()
        with g.db:
            deleted = g.db.execute(
                f"DELETE FROM {table} WHERE {condition}", params,
            )
            if not deleted.rowcount:
                abort(404)
        return redirect(url_for("history.index", client_id=client_id, q=query))

    row = g.db.execute(
        f"SELECT * FROM {table} WHERE {condition}", params,
    ).fetchone()
    if row is None:
        abort(404)
    return render_template(
        "history_delete.html", client=client,
        workout=dict(row) if grouped else workout_display(row), grouped=grouped,
    )
