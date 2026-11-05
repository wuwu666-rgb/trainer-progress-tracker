from flask import Blueprint, abort, g, redirect, render_template, request, url_for

from auth import check_csrf

bp = Blueprint("planning", __name__)


@bp.route("/planning", methods=["GET", "POST"])
@bp.route("/planning/templates/<int:template_id>/edit", methods=["GET", "POST"])
def index(template_id=None):
    name = ""
    rows = [("", "", "")]
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
            "SELECT name, target_sets, target_reps FROM template_exercises "
            "WHERE template_id = ? ORDER BY position",
            (template_id,),
        ).fetchall()

    if request.method == "POST":
        check_csrf()
        name = request.form.get("name", "").strip()
        exercises = request.form.getlist("exercise")
        sets = request.form.getlist("target_sets")
        reps = request.form.getlist("target_reps")
        rows = list(zip(exercises, sets, reps)) or rows

        try:
            if not name or not exercises or len(exercises) != len(sets) or len(sets) != len(reps):
                raise ValueError
            targets = []
            for exercise, target_sets, target_reps in rows:
                exercise = exercise.strip()
                target_sets, target_reps = int(target_sets), int(target_reps)
                if not exercise or not (0 < target_sets < 2**63 and 0 < target_reps < 2**63):
                    raise ValueError
                targets.append((exercise, target_sets, target_reps))
        except ValueError:
            error = "Enter a template name and at least one named exercise. Sets and reps must be positive whole numbers."
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
                    "(template_id, position, name, target_sets, target_reps) VALUES (?, ?, ?, ?, ?)",
                    [(template_id, position, *target) for position, target in enumerate(targets, 1)],
                )
            return redirect(url_for("planning.index"))

    templates = {}
    for exercise in g.db.execute(
        "SELECT t.id, t.name AS template_name, e.name, e.target_sets, e.target_reps "
        "FROM templates AS t JOIN template_exercises AS e ON e.template_id = t.id "
        "WHERE t.trainer_id = ? ORDER BY t.id DESC, e.position",
        (g.user["id"],),
    ):
        template = templates.setdefault(exercise["id"], {"id": exercise["id"], "name": exercise["template_name"], "exercises": []})
        template["exercises"].append(exercise)

    return render_template(
        "planning.html", templates=templates.values(), name=name, rows=rows,
        error=error, editing=template_id is not None,
    ), 400 if error else 200
