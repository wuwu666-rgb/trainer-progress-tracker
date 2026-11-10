from contextlib import closing
from pathlib import Path
import os
import secrets
import sqlite3

from flask import Flask, abort, g, redirect, render_template, request, url_for

from werkzeug.security import generate_password_hash

from auth import bp as auth, csrf_token, load_user

from clients import CLIENT_HISTORY_PROFILES, bp as clients, get_linked_profile
from planning import bp as planning, get_assigned_plans
from sessions import bp as sessions
from history import bp as history, get_chart_data, get_workouts
from workout_sessions import bp as workout_sessions

app = Flask(__name__)
app.config["DATABASE"] = Path(__file__).with_name("trainer.sqlite3")

app.config.update(
    SECRET_KEY=os.environ.get("REPBOOK_SECRET_KEY") or secrets.token_hex(32),
    SESSION_COOKIE_SAMESITE="Lax",
)
app.jinja_env.globals["csrf_token"] = csrf_token

for blueprint in (auth, clients, planning, sessions, history, workout_sessions):
    app.register_blueprint(blueprint)


@app.before_request
def open_database():
    g.db = sqlite3.connect(app.config["DATABASE"])
    g.db.row_factory = sqlite3.Row
    g.db.execute("PRAGMA foreign_keys = ON")
    load_user()
    if request.blueprint in ("clients", "planning", "sessions", "history", "workout_sessions"):
        if g.user is None:
            return redirect(url_for("auth.login"))
        if request.endpoint in ("clients.invitations", "clients.respond"):
            if g.user["role"] != "client":
                abort(403)
        elif g.user["role"] != "trainer" and request.endpoint != "clients.disconnect" and not (
            request.blueprint in ("history", "workout_sessions")
            or (request.endpoint == "planning.plan_detail" and request.method in ("GET", "HEAD"))
        ):
            abort(403)


@app.teardown_appcontext
def close_database(error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@app.get("/")
def home():
    if g.user is None:
        return redirect(url_for("auth.login"))
    if g.user["role"] == "client":
        profile = get_linked_profile()
        record_count = g.db.execute(
            f"WITH profiles AS ({CLIENT_HISTORY_PROFILES}) "
            "SELECT (SELECT COUNT(*) FROM workouts WHERE client_id IN (SELECT id FROM profiles)) + "
            "(SELECT COUNT(*) FROM cardio_workouts WHERE client_id IN (SELECT id FROM profiles)) + "
            "(SELECT COUNT(*) FROM workout_sessions WHERE client_id IN (SELECT id FROM profiles) "
            "AND completed_at IS NOT NULL)", (g.user["id"],),
        ).fetchone()[0]
        return render_template(
            "client_home.html", profile=profile, plans=get_assigned_plans(),
            record_count=record_count,
        )
    trainer_id = g.user["id"]
    overview = g.db.execute(
        "SELECT (SELECT COUNT(*) FROM clients WHERE trainer_id = ?) AS clients, "
        "(SELECT COUNT(*) FROM client_invitations AS i JOIN clients AS c ON c.id = i.client_id "
        "WHERE c.trainer_id = ? AND i.status = 'pending') AS invitations, "
        "(SELECT COUNT(*) FROM plans WHERE trainer_id = ? AND profile_id IS NULL) AS plans",
        (trainer_id, trainer_id, trainer_id),
    ).fetchone()
    return render_template("home.html", overview=overview)


@app.get("/dashboard/<page>")
def dashboard(page):
    if g.user is None:
        return redirect(url_for("auth.login"))

    if page == "account":
        trainer = g.user["role"] == "trainer"
        connections = g.db.execute(
            "SELECT id, name FROM clients WHERE trainer_id = ? AND client_user_id IS NOT NULL ORDER BY name, id",
            (g.user["id"],),
        ).fetchall() if trainer else ()
        return render_template(
            "dashboard_page.html", title="Account", dashboard_page=page,
            connections=connections, profile=None if trainer else get_linked_profile(),
        )

    if g.user["role"] != "client":
        abort(404)
    if page == "workouts":
        return render_template(
            "assigned_plans.html", dashboard_page=page, plans=get_assigned_plans(),
            profile=get_linked_profile(),
        )
    if page == "progress":
        return render_template(
            "history.html", dashboard_page=page, workouts=get_workouts(), chart_data=get_chart_data(),
        )
    abort(404)


def init_database(*, seed_demo=False):
    with closing(sqlite3.connect(app.config["DATABASE"])) as db, db:
        db.execute("PRAGMA foreign_keys = ON")
        db.executescript(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))
        db.execute("BEGIN IMMEDIATE")

        client_columns = {column[1] for column in db.execute("PRAGMA table_info(clients)")}
        if "goals" not in client_columns:
            db.execute("ALTER TABLE clients ADD COLUMN goals TEXT NOT NULL DEFAULT ''")
        if "trainer_id" not in client_columns:
            db.execute("ALTER TABLE clients ADD COLUMN trainer_id INTEGER REFERENCES users(id)")

        db.execute("CREATE INDEX IF NOT EXISTS clients_trainer_name ON clients (trainer_id, name)")
        if "client_user_id" not in client_columns:
            db.execute("ALTER TABLE clients ADD COLUMN client_user_id INTEGER REFERENCES users(id)")
        if "archived_client_user_id" not in client_columns:
            db.execute("ALTER TABLE clients ADD COLUMN archived_client_user_id INTEGER REFERENCES users(id)")
        db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS clients_linked_account "
            "ON clients (client_user_id) WHERE client_user_id IS NOT NULL"
        )

        for table in ("workouts", "cardio_workouts"):
            columns = {column[1] for column in db.execute(f"PRAGMA table_info({table})")}
            if "set_count" not in columns:
                db.execute(
                    f"ALTER TABLE {table} ADD COLUMN set_count INTEGER NOT NULL DEFAULT 1 CHECK (set_count > 0)"
                )

        for table in ("template_exercises", "plan_exercises"):
            columns = {column[1] for column in db.execute(f"PRAGMA table_info({table})")}
            if "target_weight_lb" not in columns:
                db.execute(f"ALTER TABLE {table} ADD COLUMN target_weight_lb TEXT")
            if "unit" not in columns:
                db.execute(
                    f"ALTER TABLE {table} ADD COLUMN unit TEXT NOT NULL DEFAULT 'reps' "
                    "CHECK (unit IN ('reps', 'minutes'))"
                )

        plan_columns = {column[1] for column in db.execute("PRAGMA table_info(plans)")}
        if "profile_id" not in plan_columns:
            db.execute("ALTER TABLE plans ADD COLUMN profile_id INTEGER REFERENCES clients(id)")

        # Older local templates have no known owner.
        columns = db.execute("PRAGMA table_info(templates)").fetchall()
        if not any(column[1] == "trainer_id" for column in columns):
            db.execute("ALTER TABLE templates ADD COLUMN trainer_id INTEGER REFERENCES users(id)")

        if seed_demo:
            for name, email, password, role in (
                ("Demo Trainer", "demo-trainer-84d617@example.com", "JsL_iMYZv-B1aFeo", "trainer"),
                ("Demo Client", "demo-client-2c4784@example.com", "T0Pujje4zsgrNaDL", "client"),
            ):
                if db.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
                    continue
                db.execute(
                    "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?) "
                    "ON CONFLICT(email) DO NOTHING",
                    (name, email, generate_password_hash(password), role),
                )


            db.execute(
                "INSERT INTO clients (name, trainer_id) "
                "SELECT 'Sample Client', id FROM users "
                "WHERE email = ? AND role = 'trainer' "
                "AND NOT EXISTS (SELECT 1 FROM clients WHERE trainer_id = users.id)",
                ("demo-trainer-84d617@example.com",),
            )


if __name__ == "__main__":
    init_database(seed_demo=True)
    app.run()
