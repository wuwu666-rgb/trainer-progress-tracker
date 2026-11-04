from flask import Blueprint, g, redirect, render_template, request, url_for

bp = Blueprint("planning", __name__)


@bp.route("/planning", methods=["GET", "POST"])
def index():
    name = ""
    rows = [("", "", "")]
    error = None

    if request.method == "POST":
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
                template_id = g.db.execute(
                    "INSERT INTO templates (name) VALUES (?)", (name,)
                ).lastrowid
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
        "ORDER BY t.id DESC, e.position"
    ):
        template = templates.setdefault(exercise["id"], {"name": exercise["template_name"], "exercises": []})
        template["exercises"].append(exercise)

    return render_template("planning.html", templates=templates.values(), name=name, rows=rows, error=error), (
        400 if error else 200
    )
