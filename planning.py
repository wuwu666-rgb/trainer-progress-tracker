from decimal import Decimal, InvalidOperation
from itertools import zip_longest

from flask import Blueprint, abort, g, redirect, render_template, request, url_for

from auth import check_csrf

bp = Blueprint("planning", __name__)


def read_workout_fields():
    name = request.form.get("name", "").strip()
    exercises = request.form.getlist("exercise")
    weights = request.form.getlist("target_weight_lb") or [""] * len(exercises)
    rows = list(zip_longest(
        exercises,
        request.form.getlist("target_sets"),
        request.form.getlist("target_reps"),
        weights,
        fillvalue="",
    )) or [("", "", "", "")]
    targets = []
    try:
        if not name or len(weights) != len(exercises):
            raise ValueError
        for exercise, sets, reps, weight in rows:
            exercise = exercise.strip()
            sets, reps = int(sets), int(reps)
            weight = weight.strip()
            target_weight = Decimal(weight) if weight else None
            if not exercise or not (0 < sets < 2**63 and 0 < reps < 2**63):
                raise ValueError
            if target_weight is not None and (not target_weight.is_finite() or target_weight < 0):
                raise ValueError
            targets.append((exercise, sets, reps, str(target_weight) if target_weight is not None else None))
    except (ValueError, InvalidOperation):
        return name, rows, None
    return name, rows, targets


def linked_clients():
    return g.db.execute(
        "SELECT id, name FROM clients WHERE trainer_id = ? AND client_user_id IS NOT NULL "
        "ORDER BY name, id",
        (g.user["id"],),
    ).fetchall()


@bp.route("/planning", methods=["GET", "POST"])
@bp.route("/planning/templates/<int:template_id>/edit", methods=["GET", "POST"])
def index(template_id=None):
    name = ""
    rows = [("", "", "", "")]
    error = None

    if template_id is not None:
        template = g.db.execute(
            "SELECT name FROM templates WHERE id = ? AND trainer_id = ?",
            (template_id, g.user["id"]),
        ).fetchone()
        if template is None:
            abort(404)
        name = template["name"]
        rows = g.db.execute(
            "SELECT name, target_sets, target_reps, target_weight_lb FROM template_exercises "
            "WHERE template_id = ? ORDER BY position",
            (template_id,),
        ).fetchall()

    if request.method == "POST":
        check_csrf()
        name, rows, targets = read_workout_fields()
        if targets is None:
            error = "Enter a template name and at least one named exercise. Sets and reps must be positive whole numbers. Target weight, if provided, must be zero or greater."
        else:
            with g.db:
                if template_id is None:
                    template_id = g.db.execute(
                        "INSERT INTO templates (name, trainer_id) VALUES (?, ?)", (name, g.user["id"])
                    ).lastrowid
                else:
                    updated = g.db.execute(
                        "UPDATE templates SET name = ? WHERE id = ? AND trainer_id = ?",
                        (name, template_id, g.user["id"]),
                    )
                    if not updated.rowcount:
                        abort(404)
                    g.db.execute(
                        "DELETE FROM template_exercises WHERE template_id = ?", (template_id,)
                    )
                g.db.executemany(
                    "INSERT INTO template_exercises "
                    "(template_id, position, name, target_sets, target_reps, target_weight_lb) VALUES (?, ?, ?, ?, ?, ?)",
                    [(template_id, position, *target) for position, target in enumerate(targets, 1)],
                )
            return redirect(url_for("planning.index"))

    templates = {}
    for exercise in g.db.execute(
        "SELECT t.id, t.name AS template_name, e.name, e.target_sets, e.target_reps, e.target_weight_lb "
        "FROM templates AS t JOIN template_exercises AS e ON e.template_id = t.id "
        "WHERE t.trainer_id = ? ORDER BY t.id DESC, e.position",
        (g.user["id"],),
    ):
        template = templates.setdefault(exercise["id"], {"id": exercise["id"], "name": exercise["template_name"], "exercises": []})
        template["exercises"].append(exercise)

    plans = g.db.execute(
        "SELECT p.id, p.name, c.name AS client_name FROM plans AS p "
        "LEFT JOIN clients AS c ON c.id = p.profile_id AND c.trainer_id = p.trainer_id "
        "WHERE p.trainer_id = ? ORDER BY p.id DESC",
        (g.user["id"],),
    ).fetchall()
    return render_template(
        "planning.html", plans=plans, templates=templates.values(), name=name, rows=rows,
        error=error, editing=template_id is not None,
    ), 400 if error else 200


@bp.post("/planning/templates/<int:template_id>/copy")
@bp.post("/planning/plans/from-template")
def copy_template(template_id=None):
    check_csrf()
    if template_id is None:
        template_id = request.form.get("template_id", type=int)
        if template_id is None or not 0 < template_id < 2**63:
            abort(400)
    with g.db:
        result = g.db.execute(
            "INSERT INTO plans (trainer_id, source_template_id, name) "
            "SELECT trainer_id, id, name FROM templates WHERE id = ? AND trainer_id = ?",
            (template_id, g.user["id"]),
        )
        if not result.rowcount:
            abort(404)
        plan_id = result.lastrowid
        g.db.execute(
            "INSERT INTO plan_exercises (plan_id, position, name, target_sets, target_reps, target_weight_lb) "
            "SELECT ?, position, name, target_sets, target_reps, target_weight_lb "
            "FROM template_exercises WHERE template_id = ?",
            (plan_id, template_id),
        )
    return redirect(url_for("planning.plan_detail", plan_id=plan_id))


@bp.route("/planning/plans/new", methods=["GET", "POST"])
def new_plan():
    name = ""
    rows = [("", "", "", "")]
    error = None
    if request.method == "POST":
        check_csrf()
        name, rows, targets = read_workout_fields()
        selected_profile = request.form.get("profile_id", "")
        profile_id = request.form.get("profile_id", type=int)
        if targets is None:
            error = "Enter a plan name and at least one named exercise. Sets and reps must be positive whole numbers. Target weight, if provided, must be zero or greater."
        elif selected_profile and (profile_id is None or not 0 < profile_id < 2**63):
            error = "Select one of your linked clients."
        else:
            with g.db:
                result = g.db.execute(
                    "INSERT INTO plans (trainer_id, profile_id, name) "
                    "SELECT ?, ?, ? WHERE ? IS NULL OR EXISTS ("
                    "SELECT 1 FROM clients WHERE id = ? AND trainer_id = ? AND client_user_id IS NOT NULL)",
                    (g.user["id"], profile_id, name, profile_id, profile_id, g.user["id"]),
                )
                if result.rowcount:
                    plan_id = result.lastrowid
                    g.db.executemany(
                        "INSERT INTO plan_exercises (plan_id, position, name, target_sets, target_reps, target_weight_lb) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        [(plan_id, position, *target) for position, target in enumerate(targets, 1)],
                    )
                else:
                    error = "Select one of your linked clients."
            if error is None:
                return redirect(url_for("planning.plan_detail", plan_id=plan_id))
    templates = g.db.execute(
        "SELECT id, name FROM templates WHERE trainer_id = ? ORDER BY name, id",
        (g.user["id"],),
    ).fetchall()
    return render_template(
        "new_plan.html", name=name, rows=rows, clients=linked_clients(),
        templates=templates, error=error, reorder=True,
    ), 400 if error else 200


def get_assigned_plans():
    return g.db.execute(
        "SELECT p.id, p.name FROM plans AS p "
        "JOIN clients AS c ON c.id = p.profile_id AND c.trainer_id = p.trainer_id "
        "WHERE c.client_user_id = ? ORDER BY p.id DESC",
        (g.user["id"],),
    ).fetchall()


def get_visible_plan(plan_id):
    access = "p.trainer_id" if g.user["role"] == "trainer" else "c.client_user_id"
    plan = g.db.execute(
        "SELECT p.id, p.name, p.profile_id, c.name AS client_name FROM plans AS p "
        "LEFT JOIN clients AS c ON c.id = p.profile_id AND c.trainer_id = p.trainer_id "
        f"WHERE p.id = ? AND {access} = ?",
        (plan_id, g.user["id"]),
    ).fetchone()
    if plan is None:
        abort(404)
    return plan


def get_plan_exercises(plan_id):
    return g.db.execute(
        "SELECT name, target_sets, target_reps, target_weight_lb FROM plan_exercises "
        "WHERE plan_id = ? ORDER BY position",
        (plan_id,),
    ).fetchall()


@bp.route("/planning/plans/<int:plan_id>", methods=["GET", "POST"])
def plan_detail(plan_id):
    trainer = g.user["role"] == "trainer"
    plan = get_visible_plan(plan_id)
    error = None
    status = 200
    if request.method == "POST":
        check_csrf()
        profile_id = request.form.get("profile_id", type=int)
        if plan["profile_id"] is not None:
            if plan["profile_id"] == profile_id:
                return redirect(url_for("planning.plan_detail", plan_id=plan_id))
            error = "This plan has already been assigned."
            status = 409
        elif profile_id is None or not 0 < profile_id < 2**63:
            error = "Select one of your linked clients."
            status = 400
        else:
            with g.db:
                result = g.db.execute(
                    "UPDATE plans SET profile_id = ? "
                    "WHERE id = ? AND trainer_id = ? AND profile_id IS NULL "
                    "AND EXISTS (SELECT 1 FROM clients WHERE id = ? "
                    "AND trainer_id = plans.trainer_id AND client_user_id IS NOT NULL)",
                    (profile_id, plan_id, g.user["id"], profile_id),
                )
            if result.rowcount:
                return redirect(url_for("planning.plan_detail", plan_id=plan_id))
            error = "The plan could not be assigned. Check the linked client or reload the page."
            status = 409

    return render_template(
        "plan_detail.html", plan=plan, exercises=get_plan_exercises(plan_id), error=error,
        clients=linked_clients() if trainer and plan["profile_id"] is None else (),
    ), status

@bp.route("/planning/<collection>/<int:item_id>/delete", methods=["GET", "POST"])
def delete_item(collection, item_id):
    if collection not in ("templates", "plans"):
        abort(404)

    is_template = collection == "templates"
    owner = (item_id, g.user["id"])
    columns = "name" if is_template else "name, profile_id"
    item = g.db.execute(
        f"SELECT {columns} FROM {collection} WHERE id = ? AND trainer_id = ?", owner
    ).fetchone()
    if item is None:
        abort(404)

    can_delete = is_template or item["profile_id"] is None
    status = 200
    if request.method == "POST":
        check_csrf()
        condition = "" if is_template else " AND profile_id IS NULL"
        with g.db:
            result = g.db.execute(
                f"DELETE FROM {collection} WHERE id = ? AND trainer_id = ?{condition}", owner
            )
        if result.rowcount:
            return redirect(url_for("planning.index", _anchor=None if is_template else "saved-plans"))
        can_delete = False
        status = 409

    return render_template(
        "planning_delete.html", item=item, item_id=item_id, is_template=is_template,
        can_delete=can_delete,
    ), status
