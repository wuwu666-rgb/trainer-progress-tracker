from pathlib import Path
import os
import secrets
import sqlite3

from flask import Flask, abort, g, redirect, render_template, request, url_for

from auth import bp as auth, csrf_token, load_user

from clients import bp as clients
from planning import bp as planning
from sessions import bp as sessions
from history import bp as history

app = Flask(__name__)
app.config["DATABASE"] = Path(__file__).with_name("trainer.sqlite3")

app.config.update(
    SECRET_KEY=os.environ.get("REPBOOK_SECRET_KEY") or secrets.token_hex(32),
    SESSION_COOKIE_SAMESITE="Lax",
)
app.jinja_env.globals["csrf_token"] = csrf_token

for blueprint in (auth, clients, planning, sessions, history):
    app.register_blueprint(blueprint)


@app.before_request
def open_database():
    g.db = sqlite3.connect(app.config["DATABASE"])
    g.db.row_factory = sqlite3.Row
    g.db.execute("PRAGMA foreign_keys = ON")
    load_user()
    if request.blueprint in ("clients", "planning", "sessions", "history"):
        if g.user is None:
            return redirect(url_for("auth.login"))
        if g.user["role"] != "trainer":
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
        return render_template("client_home.html")
    return render_template("home.html")


def init_database():
    with sqlite3.connect(app.config["DATABASE"]) as db:
        db.executescript(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))


if __name__ == "__main__":
    init_database()
    app.run()
