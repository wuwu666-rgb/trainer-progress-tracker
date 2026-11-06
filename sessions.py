from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, g, redirect, render_template, request, url_for

from auth import check_csrf
from clients import get_visible_client

bp = Blueprint("sessions", __name__)


@bp.route("/clients/<int:client_id>/record", methods=["GET", "POST"])
def record(client_id):
    client = get_visible_client(client_id)
    today = date.today()
    result_unit = request.form.get("result_unit")
    if result_unit is not None:
        exercise_type = {"reps": "strength", "minutes": "cardio"}.get(result_unit)
    elif request.method == "POST":
        exercise_type = request.form.get("exercise_type", "strength")
    else:
        exercise_type = "cardio" if request.args.get("mode") == "cardio" else "strength"
    timed = exercise_type == "cardio"
    legacy_field = "duration_min" if timed else "reps"
    result = request.form.get("result", request.form.get(legacy_field, ""))
    error = None

    if request.method == "POST":
        check_csrf()
        exercise = request.form.get("exercise", "").strip()
        try:
            workout_date = date.fromisoformat(request.form.get("workout_date", ""))
            if not exercise or workout_date > today:
                raise ValueError
        except ValueError:
            error = "Enter an exercise and a valid date that is not in the future."

        if error is None:
            set_count = request.form.get("set_count", default=None, type=int)
            if "set_count" not in request.form:
                set_count = 1
            if set_count is None or not 0 < set_count < 2**63:
                error = "Enter a positive whole number of sets."

        if error is None:
            values = (client_id, workout_date.isoformat(), exercise)
            try:
                if exercise_type == "cardio":
                    duration = Decimal(result)
                    distance_text = request.form.get("distance_km", "").strip()
                    distance = Decimal(distance_text) if distance_text else None
                    if (not duration.is_finite() or duration <= 0
                            or (distance is not None and (not distance.is_finite() or distance < 0))):
                        raise ValueError
                    with g.db:
                        g.db.execute(
                            "INSERT INTO cardio_workouts "
                            "(client_id, workout_date, exercise, duration_min, distance_km, set_count) "
                            "VALUES (?, ?, ?, ?, ?, ?)",
                            (*values, str(duration), str(distance) if distance is not None else None, set_count),
                        )
                elif exercise_type in ("bodyweight", "weighted", "strength"):
                    reps = int(result)
                    weight_text = request.form.get("weight_lb", "").strip()
                    weight = Decimal((weight_text or "0") if exercise_type != "bodyweight" else "0")
                    if (not 0 < reps < 2**63
                            or not weight.is_finite() or weight < 0
                            or (exercise_type == "weighted" and weight.is_zero())):
                        raise ValueError
                    with g.db:
                        g.db.execute(
                            "INSERT INTO workouts (client_id, workout_date, exercise, reps, weight_lb, set_count) "
                            "VALUES (?, ?, ?, ?, ?, ?)",
                            (*values, reps, str(weight), set_count),
                        )
                else:
                    raise ValueError
            except (ValueError, InvalidOperation):
                error = {
                    "cardio": "Enter a positive duration and, if provided, a nonnegative distance.",
                    "bodyweight": "Enter positive whole-number reps.",
                    "weighted": "Enter positive whole-number reps and an added weight greater than zero.",
                    "strength": "Enter positive whole-number reps per set. Added weight is optional and must be zero or greater.",
                }.get(exercise_type, "Choose reps or minutes.")
            else:
                return redirect(url_for(
                    "history.index", client_id=client_id, q=request.args.get("q") or None,
                ))

    return render_template(
        "record.html", client=client, today=today.isoformat(), error=error,
        timed=timed, result=result,
    )
