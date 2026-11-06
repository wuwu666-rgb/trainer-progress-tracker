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
    exercise_type = request.form.get("exercise_type", "strength")
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
            values = (client_id, workout_date.isoformat(), exercise)
            try:
                if exercise_type == "cardio":
                    duration = Decimal(request.form.get("duration_min", ""))
                    distance_text = request.form.get("distance_km", "").strip()
                    distance = Decimal(distance_text) if distance_text else None
                    if (not duration.is_finite() or duration <= 0
                            or (distance is not None and (not distance.is_finite() or distance < 0))):
                        raise ValueError
                    with g.db:
                        g.db.execute(
                            "INSERT INTO cardio_workouts "
                            "(client_id, workout_date, exercise, duration_min, distance_km) "
                            "VALUES (?, ?, ?, ?, ?)",
                            (*values, str(duration), str(distance) if distance is not None else None),
                        )
                elif exercise_type == "strength":
                    reps = int(request.form.get("reps", ""))
                    weight = Decimal(request.form.get("weight_lb", "").strip() or "0")
                    if not 0 < reps < 2**63 or not weight.is_finite() or weight < 0:
                        raise ValueError
                    with g.db:
                        g.db.execute(
                            "INSERT INTO workouts (client_id, workout_date, exercise, reps, weight_lb) "
                            "VALUES (?, ?, ?, ?, ?)",
                            (*values, reps, str(weight)),
                        )
                else:
                    raise ValueError
            except (ValueError, InvalidOperation):
                error = {
                    "cardio": "Enter a positive duration and, if provided, a nonnegative distance.",
                    "strength": "Enter positive whole-number reps. Added weight is optional and must be zero or greater.",
                }.get(exercise_type, "Choose Strength or Cardio.")
            else:
                return redirect(url_for(
                "history.index", client_id=client_id, q=request.args.get("q") or None,
            ))

    return render_template(
        "record.html", client=client, today=today.isoformat(), error=error,
        exercise_type=exercise_type,
    )
