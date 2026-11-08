from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, abort, g, redirect, render_template, request, url_for

from auth import check_csrf
from clients import CLIENT_HISTORY_PROFILES, get_visible_client
from training_dates import today_in_new_york

bp = Blueprint("history", __name__)


def profile_scope(client_id):
    if client_id is None:
        return CLIENT_HISTORY_PROFILES, g.user["id"]
    return "SELECT ?", client_id


@bp.get("/clients/<int:client_id>/body-weights")
@bp.get("/dashboard/progress/body-weights")
def body_weights(client_id=None):
    if client_id is None and g.user["role"] != "client":
        abort(404)
    client = get_visible_client(client_id, include_archived=True) if client_id is not None else None
    scope, profile = profile_scope(client_id)
    entries = g.db.execute(
        "SELECT id, measurement_date, weight_lb FROM body_weights "
        f"WHERE client_id IN ({scope}) ORDER BY measurement_date DESC, id DESC", (profile,),
    ).fetchall()
    return render_template("body_weights.html", client=client, entries=entries)


@bp.route("/clients/<int:client_id>/body-weights/new", methods=["GET", "POST"])
@bp.route("/clients/<int:client_id>/body-weights/<int:entry_id>/edit", methods=["GET", "POST"])
def edit_body_weight(client_id, entry_id=None):
    if g.user["role"] != "trainer":
        abort(403)
    if not 0 < client_id < 2**63 or (entry_id is not None and not 0 < entry_id < 2**63):
        abort(404)
    client = get_visible_client(client_id)
    today = today_in_new_york().isoformat()
    entry = None
    if entry_id is not None:
        entry = g.db.execute(
            "SELECT measurement_date, weight_lb, revision FROM body_weights WHERE id = ? AND client_id = ?",
            (entry_id, client_id),
        ).fetchone()
        if entry is None:
            abort(404)
    measurement_date = entry["measurement_date"] if entry else today
    weight = entry["weight_lb"] if entry else ""
    revision = entry["revision"] if entry else None
    error, status = None, 200
    if request.method == "POST":
        check_csrf()
        measurement_date = request.form.get("measurement_date", "")
        weight = request.form.get("weight_lb", "").strip()
        try:
            if date.fromisoformat(measurement_date).isoformat() != measurement_date or measurement_date > today:
                raise ValueError
        except ValueError:
            error = "Choose a valid date on or before today."
        if error is None:
            try:
                if len(weight) > 64:
                    raise ValueError
                value = Decimal(weight)
                if not value.is_finite() or value <= 0:
                    raise ValueError
            except (InvalidOperation, ValueError):
                error = "Enter a body weight greater than zero."
        if error:
            status = 400
        else:
            with g.db:
                g.db.execute("BEGIN IMMEDIATE")
                get_visible_client(client_id)
                if entry and request.form.get("revision") != str(revision):
                    return redirect(url_for("history.edit_body_weight", client_id=client_id, entry_id=entry_id, stale=1))
                duplicate = g.db.execute(
                    "SELECT id FROM body_weights WHERE client_id = ? AND measurement_date = ? AND id IS NOT ?",
                    (client_id, measurement_date, entry_id),
                ).fetchone()
                if duplicate:
                    error, status = "A measurement already exists for this date. Edit it from Body-weight history.", 409
                elif entry:
                    updated = g.db.execute(
                        "UPDATE body_weights SET measurement_date = ?, weight_lb = ?, revision = revision + 1 "
                        "WHERE id = ? AND client_id = ? AND revision = ?",
                        (measurement_date, str(value), entry_id, client_id, revision),
                    )
                    if not updated.rowcount:
                        return redirect(url_for("history.edit_body_weight", client_id=client_id, entry_id=entry_id, stale=1))
                else:
                    g.db.execute(
                        "INSERT INTO body_weights (client_id, recorded_by, measurement_date, weight_lb) VALUES (?, ?, ?, ?)",
                        (client_id, g.user["id"], measurement_date, str(value)),
                    )
            if error is None:
                return redirect(url_for("history.body_weights", client_id=client_id))
    elif request.args.get("stale") and entry:
        error = "This measurement changed. Review the current values before saving."
    return render_template(
        "body_weight_form.html", client=client, entry=entry, measurement_date=measurement_date,
        weight=weight, revision=revision, today=today, error=error,
    ), status


def get_workouts(client_id=None):
    scope, profile = profile_scope(client_id)
    rows = g.db.execute(
        "SELECT id, workout_date, exercise, reps, weight_lb, set_count, "
        f"NULL AS duration_min, NULL AS distance_km FROM workouts WHERE client_id IN ({scope}) "
        "UNION ALL "
        "SELECT id, workout_date, exercise, NULL, NULL, set_count, duration_min, distance_km "
        f"FROM cardio_workouts WHERE client_id IN ({scope}) "
        "ORDER BY workout_date DESC, id DESC",
        (profile, profile),
    ).fetchall()
    sessions = g.db.execute(
        f"""
        WITH recorded_sets AS (
            SELECT w.id, w.workout_date, w.plan_name, w.recorder_id, e.id AS exercise_id,
                   recorder.name AS recorder_name, recorder.role AS recorder_role,
                   e.name, e.unit, s.result, s.weight_lb,
                   ROW_NUMBER() OVER (PARTITION BY w.id ORDER BY e.position, s.position) AS set_order
            FROM workout_sessions AS w
            JOIN workout_session_exercises AS e ON e.workout_id = w.id
            JOIN workout_session_sets AS s ON s.exercise_id = e.id
            LEFT JOIN users AS recorder ON recorder.id = w.recorder_id
            WHERE w.client_id IN ({scope}) AND w.completed_at IS NOT NULL
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
        (profile,),
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
    client = get_visible_client(client_id, include_archived=True)
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
            g.db.execute("BEGIN IMMEDIATE")
            get_visible_client(client_id)
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
