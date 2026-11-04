from pathlib import Path
import sqlite3

from flask import Flask, g, render_template

from clients import bp as clients
from planning import bp as planning
from sessions import bp as sessions
from history import bp as history

app = Flask(__name__)
app.config["DATABASE"] = Path(__file__).with_name("trainer.sqlite3")

for blueprint in (clients, planning, sessions, history):
    app.register_blueprint(blueprint)


@app.before_request
def open_database():
    g.db = sqlite3.connect(app.config["DATABASE"])
    g.db.row_factory = sqlite3.Row
    g.db.execute("PRAGMA foreign_keys = ON")


@app.teardown_appcontext
def close_database(error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@app.get("/")
def home():
    return render_template("home.html")


def init_database():
    with sqlite3.connect(app.config["DATABASE"]) as db:
        db.executescript(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))


if __name__ == "__main__":
    init_database()
    app.run()
