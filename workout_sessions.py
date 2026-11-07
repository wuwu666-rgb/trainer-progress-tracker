from datetime import date
from decimal import Decimal, InvalidOperation
from itertools import zip_longest

from flask import Blueprint, abort, g, redirect, render_template, request, url_for

from auth import check_csrf
from clients import get_visible_client
from planning import get_plan_exercises, get_visible_plan

bp = Blueprint("workout_sessions", __name__)


def drafts_for_client(client_id):
    return g.db.execute(
        "SELECT id, plan_name, workout_date FROM workout_sessions "
        "WHERE client_id = ? AND recorder_id = ? AND completed_at IS NULL ORDER BY id DESC",
        (client_id, g.user["id"]),
    ).fetchall()


def start_workout(client, plan=None):
    plan_id = plan["id"] if plan else None
    draft = g.db.execute(
        "SELECT id FROM workout_sessions WHERE client_id = ? AND recorder_id = ? "
        "AND completed_at IS NULL AND source_plan_id IS ? "
        "AND (? IS NOT NULL OR plan_name IS NULL)",
        (client["id"], g.user["id"], plan_id, plan_id),
    ).fetchone()
    if draft is not None:
        return draft["id"]

    workout_id = g.db.execute(
        "INSERT INTO workout_sessions (client_id, recorder_id, source_plan_id, plan_name, workout_date) "
        "VALUES (?, ?, ?, ?, ?)",
        (client["id"], g.user["id"], plan_id, plan["name"] if plan else None, date.today().isoformat()),
    ).lastrowid
    if plan:
        g.db.executemany(
            "INSERT INTO workout_session_exercises "
            "(workout_id, position, name, unit, target_sets, target_reps, target_weight_lb) "
            "VALUES (?, ?, ?, 'reps', ?, ?, ?)",
            (
                (workout_id, position, row["name"], row["target_sets"], row["target_reps"], row["target_weight_lb"])
                for position, row in enumerate(get_plan_exercises(plan_id), 1)
            ),
        )
    return workout_id


def coached_plans(client_id):
    return g.db.execute(
        "SELECT p.id, p.name, EXISTS (SELECT 1 FROM workout_sessions AS w "
        "WHERE w.source_plan_id = p.id AND w.client_id = ? AND w.recorder_id = p.trainer_id "
        "AND w.completed_at IS NULL) AS in_progress "
        "FROM plans AS p WHERE p.trainer_id = ? "
        "AND (p.profile_id IS NULL OR p.profile_id = ?) ORDER BY p.name, p.id",
        (client_id, g.user["id"], client_id),
    ).fetchall()


@bp.get("/clients/<int:client_id>/workouts/available-plans")
def available_plans(client_id):
    if g.user["role"] != "trainer":
        abort(403)
    get_visible_client(client_id)
    plans = [
        {"id": str(plan["id"]), "name": plan["name"], "in_progress": bool(plan["in_progress"])}
        for plan in coached_plans(client_id)
    ]
    return {"plans": plans}, 200, {"Cache-Control": "no-store"}


@bp.route("/clients/<int:client_id>/workouts/start", methods=["GET", "POST"])
def start_trainer(client_id):
    if g.user["role"] != "trainer":
        abort(403)
    if request.method == "POST":
        check_csrf()
        selected_plan = request.form.get("plan_id", "")
        plan_id = request.form.get("plan_id", type=int)
        if selected_plan and (plan_id is None or not 0 < plan_id < 2**63):
            abort(400)
        with g.db:
            g.db.execute("BEGIN IMMEDIATE")
            client = get_visible_client(client_id)
            plan = get_visible_plan(plan_id) if selected_plan else None
            if plan is not None and plan["profile_id"] not in (None, client_id):
                abort(404)
            workout_id = start_workout(client, plan)
        return redirect(url_for(
            "workout_sessions.record", workout_id=workout_id, q=request.args.get("q") or None,
        ))

    client = get_visible_client(client_id)
    return render_template(
        "workout_start.html", client=client, plans=coached_plans(client_id), drafts=drafts_for_client(client_id),
    )


@bp.post("/planning/plans/<int:plan_id>/start-workout")
def start_client(plan_id):
    if g.user["role"] != "client":
        abort(403)
    check_csrf()
    with g.db:
        g.db.execute("BEGIN IMMEDIATE")
        plan = get_visible_plan(plan_id)
        client = get_visible_client(plan["profile_id"])
        workout_id = start_workout(client, plan)
    return redirect(url_for("workout_sessions.record", workout_id=workout_id))


def get_workout(workout_id):
    workout = g.db.execute(
        "SELECT * FROM workout_sessions WHERE id = ?", (workout_id,),
    ).fetchone()
    if workout is None:
        abort(404)
    return workout, get_visible_client(workout["client_id"])


def get_exercises(workout_id):
    exercises = {}
    for row in g.db.execute(
        "SELECT e.id, e.name, e.unit, e.target_sets, e.target_reps, e.target_weight_lb, "
        "s.position AS set_position, s.result, s.weight_lb "
        "FROM workout_session_exercises AS e "
        "LEFT JOIN workout_session_sets AS s ON s.exercise_id = e.id "
        "WHERE e.workout_id = ? ORDER BY e.position, s.position",
        (workout_id,),
    ):
        key = str(row["id"])
        exercise = exercises.setdefault(key, {
            "key": key, "name": row["name"], "unit": row["unit"],
            "target_sets": row["target_sets"], "target_reps": row["target_reps"],
            "target_weight_lb": row["target_weight_lb"], "sets": [],
        })
        if row["set_position"] is not None:
            exercise["sets"].append((row["result"] or "", row["weight_lb"] or ""))
    return exercises


def blank_exercise(key="new-0"):
    return {
        "key": key, "name": "", "unit": "reps", "target_sets": None,
        "target_reps": None, "target_weight_lb": None, "sets": [],
    }


def read_exercises(saved, trainer):
    keys = request.form.getlist("exercise_key")
    planned_keys = [key for key, exercise in saved.items() if exercise["target_sets"] is not None]
    if (len(keys) != len(set(keys))
            or [key for key in keys if key in planned_keys] != planned_keys):
        abort(400)
    if not trainer and keys != list(saved):
        abort(400, description="Record results for the exercises already in this workout.")
    exercises = []
    for key in keys:
        if key not in saved and not (key.startswith("new-") and key[4:].isascii() and key[4:].isdigit()):
            abort(400)
        exercise = dict(saved[key]) if key in saved else blank_exercise(key)
        if trainer and exercise["target_sets"] is None:
            exercise["name"] = request.form.get(f"name_{key}", "").strip()
            exercise["unit"] = request.form.get(f"unit_{key}", "")
        exercise["sets"] = list(zip_longest(
            request.form.getlist(f"result_{key}"), request.form.getlist(f"weight_{key}"),
            fillvalue="",
        ))
        exercises.append(exercise)
    return exercises


def parse_set(result, weight, unit):
    result, weight = result.strip(), weight.strip()
    if len(result) > 64 or len(weight) > 64:
        raise ValueError
    if result:
        value = int(result) if unit == "reps" else Decimal(result)
        if (unit == "reps" and not 0 < value < 2**63
                or unit == "minutes" and (not value.is_finite() or value <= 0)):
            raise ValueError
        result = str(value)
    if weight and unit == "reps":
        value = Decimal(weight)
        if not value.is_finite() or value < 0:
            raise ValueError
        weight = str(value) if value else ""
    else:
        weight = ""
    return result or None, weight or None


def validated_exercises(exercises, complete):
    parsed = []
    for position, exercise in enumerate(exercises, 1):
        label = exercise["name"] or f"Exercise {position}"
        if exercise["unit"] not in ("reps", "minutes"):
            raise ValueError(f"{label}: choose reps or minutes.")
        if exercise["target_sets"] is None and len(exercise["name"]) > 120:
            raise ValueError(f"Exercise {position}: use a name of 120 characters or fewer.")
        sets = []
        for number, (result, weight) in enumerate(exercise["sets"], 1):
            try:
                result, weight = parse_set(result, weight, exercise["unit"])
            except (ValueError, InvalidOperation):
                metric = "positive whole-number reps and an optional nonnegative weight"
                if exercise["unit"] == "minutes":
                    metric = "a positive duration in minutes"
                raise ValueError(f"{label}, set {number}: enter {metric}.") from None
            if complete:
                if result is None and weight is not None:
                    raise ValueError(f"{label}, set {number}: enter reps or clear the weight.")
                if result is None:
                    continue
                if not exercise["name"]:
                    raise ValueError(f"Name exercise {position} before finishing this workout.")
            sets.append((result, weight))
        if not complete or sets or exercise["target_sets"] is not None:
            parsed.append(dict(exercise, sets=sets))
    if complete and not any(exercise["sets"] for exercise in parsed):
        raise ValueError("Record at least one set before finishing this workout.")
    return parsed


def save_workout(workout_id, revision, workout_date, exercises, complete):
    # Lock the draft revision before replacing its exercises and sets.
    updated = g.db.execute(
        "UPDATE workout_sessions SET workout_date = ?, revision = revision + 1, "
        "completed_at = CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE NULL END "
        "WHERE id = ? AND revision = ? AND recorder_id = ? AND completed_at IS NULL",
        (workout_date, complete, workout_id, revision, g.user["id"]),
    )
    if not updated.rowcount:
        return False
    g.db.execute("DELETE FROM workout_session_exercises WHERE workout_id = ?", (workout_id,))
    for position, exercise in enumerate(exercises, 1):
        exercise_id = g.db.execute(
            "INSERT INTO workout_session_exercises "
            "(workout_id, position, name, unit, target_sets, target_reps, target_weight_lb) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                workout_id, position, exercise["name"], exercise["unit"],
                exercise["target_sets"], exercise["target_reps"], exercise["target_weight_lb"],
            ),
        ).lastrowid
        g.db.executemany(
            "INSERT INTO workout_session_sets (exercise_id, position, result, weight_lb) VALUES (?, ?, ?, ?)",
            ((exercise_id, number, *values) for number, values in enumerate(exercise["sets"], 1)),
        )
    return True


def detail_url(workout_id):
    return url_for("workout_sessions.detail", workout_id=workout_id, q=request.args.get("q") or None)


@bp.route("/workouts/<int:workout_id>/record", methods=["GET", "POST"])
def record(workout_id):
    with g.db:
        g.db.execute("BEGIN")
        workout, client = get_workout(workout_id)
        if workout["recorder_id"] != g.user["id"]:
            abort(404)
        if request.method == "POST":
            check_csrf()
        if workout["completed_at"]:
            return redirect(detail_url(workout_id))
        saved = get_exercises(workout_id)

    trainer = g.user["role"] == "trainer"
    today = date.today().isoformat()
    exercises = list(saved.values())
    workout_date = workout["workout_date"]
    revision = workout["revision"]
    error = None
    status = 200
    if request.method == "POST":
        revision = request.form.get("revision", type=int)
        action = request.form.get("action")
        if revision is None or not 0 <= revision < 2**63 or action not in ("save", "complete", "discard"):
            abort(400)
        if action == "discard":
            with g.db:
                discarded = g.db.execute(
                    "DELETE FROM workout_sessions WHERE id = ? AND revision = ? AND recorder_id = ? "
                    "AND completed_at IS NULL",
                    (workout_id, revision, g.user["id"]),
                )
            if not discarded.rowcount:
                abort(409)
            return redirect(
                url_for("workout_sessions.start_trainer", client_id=client["id"], q=request.args.get("q") or None)
                if trainer else url_for("dashboard", page="workouts")
            )

        if revision != workout["revision"]:
            error = "This draft changed in another tab. Reopen the saved workout to continue."
            status = 409
        else:
            exercises = read_exercises(saved, trainer)
            if trainer:
                workout_date = request.form.get("workout_date", "")
            complete = action == "complete"
            try:
                if date.fromisoformat(workout_date).isoformat() != workout_date or workout_date > today:
                    raise ValueError
            except ValueError:
                error = "Choose a valid workout date on or before today."
                status = 400
            if error is None:
                try:
                    parsed = validated_exercises(exercises, complete)
                except ValueError as problem:
                    error = str(problem)
                    status = 400
                else:
                    with g.db:
                        updated = save_workout(workout_id, revision, workout_date, parsed, complete)
                    if updated:
                        return redirect(detail_url(workout_id) if complete else url_for(
                            "workout_sessions.record", workout_id=workout_id, saved=1,
                            q=request.args.get("q") or None,
                        ))
                    current, _ = get_workout(workout_id)
                    if current["completed_at"]:
                        return redirect(detail_url(workout_id))
                    error = "This draft changed in another tab. Reopen the saved workout to continue."
                    status = 409

    return render_template(
        "workout_record.html", workout=workout, client=client,
        exercises=exercises or ([blank_exercise()] if trainer else []),
        blank_exercise=blank_exercise("__KEY__"),
        revision=revision, workout_date=workout_date, today=today, error=error, conflict=status == 409,
    ), status


@bp.get("/workouts/<int:workout_id>")
def detail(workout_id):
    workout, client = get_workout(workout_id)
    if not workout["completed_at"]:
        abort(404)
    return render_template(
        "workout_detail.html", workout=workout, client=client, exercises=get_exercises(workout_id).values(),
    )
