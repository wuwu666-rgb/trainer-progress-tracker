import re
import secrets

from flask import Blueprint, abort, g, redirect, render_template, request, session, url_for
from werkzeug.security import generate_password_hash

bp = Blueprint("auth", __name__)


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def check_csrf():
    expected = session.get("csrf_token", "")
    supplied = request.form.get("csrf_token", "")
    if not expected or not secrets.compare_digest(expected.encode(), supplied.encode()):
        abort(400)


@bp.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        check_csrf()
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "")

        if not name or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            error = "Enter a name and a valid email address."
        elif not password or len(password) > 256 or role not in ("trainer", "client"):
            error = "Enter a password of up to 256 characters and select a role."
        else:
            with g.db:
                result = g.db.execute(
                    "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?) "
                    "ON CONFLICT(email) DO NOTHING",
                    (name, email, generate_password_hash(password), role),
                )
            if result.rowcount:
                return redirect(url_for("auth.register", registered=1))
            error = "An account already uses that email address."

    return render_template("auth.html", registering=True, error=error), 400 if error else 200
