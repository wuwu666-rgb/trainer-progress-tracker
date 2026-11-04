from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, abort, g, redirect, render_template, request, url_for

bp = Blueprint("sessions", __name__)


@bp.route("/clients/<int:client_id>/record", methods=["GET", "POST"])
def record(client_id):
    client = g.db.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
    if client is None:
        abort(404)

    today = date.today().isoformat()
    error = None
    if request.method == "POST":
        exercise = request.form.get("exercise", "").strip()
        try:
            workout_date = date.fromisoformat(request.form.get("workout_date", ""))
            reps = int(request.form.get("reps", ""))
            weight = Decimal(request.form.get("weight_lb", ""))
            if (not exercise or workout_date > date.today() or reps <= 0
                    or not weight.is_finite() or weight < 0):
                raise ValueError
        except (ValueError, InvalidOperation):
            error = "Enter an exercise, a valid date, positive reps, and a nonnegative weight."
        else:
            with g.db:
                g.db.execute(
                    "INSERT INTO workouts (client_id, workout_date, exercise, reps, weight_lb) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (client_id, workout_date.isoformat(), exercise, reps, str(weight)),
                )
            return redirect(url_for("history.index", client_id=client_id))

    return render_template("record.html", client=client, today=today, error=error)
