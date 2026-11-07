from flask import Blueprint, abort, g, redirect, render_template, request, url_for

from auth import check_csrf

bp = Blueprint("clients", __name__)

CLIENTS_PER_PAGE = 8

def get_visible_client(client_id):
    owner_column = "trainer_id" if g.user["role"] == "trainer" else "client_user_id"
    client = g.db.execute(
        f"SELECT id, name, goals, client_user_id FROM clients WHERE id = ? AND {owner_column} = ?",
        (client_id, g.user["id"]),
    ).fetchone()
    if client is None:
        abort(404)
    return client


@bp.route("/clients", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        return new_client()
    trainer_id = g.user["id"]
    query = request.args.get("q", "").strip()[:100]
    page = max(1, request.args.get("page", default=1, type=int))
    focus = request.args.get("focus", type=int)
    search = "trainer_id = ? AND instr(lower(name), lower(?)) > 0"

    if focus is not None and 0 < focus < 2**63:
        target = g.db.execute(
            "SELECT name, instr(lower(name), lower(?)) AS matches "
            "FROM clients WHERE id = ? AND trainer_id = ?",
            (query, focus, trainer_id),
        ).fetchone()
        if target is not None:
            if not target["matches"]:
                query = ""
            position = g.db.execute(
                f"SELECT COUNT(*) FROM clients WHERE {search} AND (name, id) < (?, ?)",
                (trainer_id, query, target["name"], focus),
            ).fetchone()[0]
            page = position // CLIENTS_PER_PAGE + 1

    total = g.db.execute(
        f"SELECT COUNT(*) FROM clients WHERE {search}", (trainer_id, query)
    ).fetchone()[0]
    pages = max(1, (total + CLIENTS_PER_PAGE - 1) // CLIENTS_PER_PAGE)
    page = min(page, pages)
    offset = (page - 1) * CLIENTS_PER_PAGE
    clients = g.db.execute(
        f"SELECT id, name, goals, client_user_id FROM clients WHERE {search} "
        "ORDER BY name, id LIMIT ? OFFSET ?",
        (trainer_id, query, CLIENTS_PER_PAGE, offset),
    ).fetchall()
    return render_template(
        "clients.html", clients=clients, query=query, page=page, pages=pages, total=total,
        first=offset + 1, last=offset + len(clients),
    )


@bp.route("/clients/new", methods=["GET", "POST"])
def new_client():
    error = None
    if request.method == "POST":
        check_csrf()
        name = request.form.get("name", "").strip()
        goals = request.form.get("goals", "").strip()

        if not name:
            error = "Enter a client name."
        else:
            with g.db:
                new_profile = g.db.execute(
                    "INSERT INTO clients (name, goals, trainer_id) VALUES (?, ?, ?)",
                    (name, goals, g.user["id"]),
                )
            client_id = new_profile.lastrowid
            return redirect(url_for("clients.index", focus=client_id, _anchor=f"client-{client_id}"))

    return render_template("client_new.html", error=error), 400 if error else 200


@bp.route("/clients/<int:client_id>/edit", methods=["GET", "POST"])
def edit(client_id):
    trainer_id = g.user["id"]
    client = g.db.execute(
        "SELECT id, name, goals FROM clients WHERE id = ? AND trainer_id = ?",
        (client_id, trainer_id),
    ).fetchone()
    if client is None:
        abort(404)

    error = None
    if request.method == "POST":
        check_csrf()
        name = request.form.get("name", "").strip()
        goals = request.form.get("goals", "").strip()
        if not name:
            error = "Enter a client name."
        else:
            with g.db:
                result = g.db.execute(
                    "UPDATE clients SET name = ?, goals = ? WHERE id = ? AND trainer_id = ?",
                    (name, goals, client_id, trainer_id),
                )
                if not result.rowcount:
                    abort(404)
            return redirect(url_for(
                "clients.index", focus=client_id, q=request.args.get("q") or None,
                _anchor=f"client-{client_id}",
            ))

    return render_template("client_edit.html", profile=client, error=error), 400 if error else 200


@bp.route("/clients/<int:client_id>/delete", methods=["GET", "POST"])
def delete(client_id):
    profile = get_visible_client(client_id)
    unused_profile = (
        "client_user_id IS NULL "
        "AND NOT EXISTS (SELECT 1 FROM workouts WHERE client_id = clients.id) "
        "AND NOT EXISTS (SELECT 1 FROM cardio_workouts WHERE client_id = clients.id) "
        "AND NOT EXISTS (SELECT 1 FROM workout_sessions WHERE client_id = clients.id) "
        "AND NOT EXISTS (SELECT 1 FROM body_weights WHERE client_id = clients.id) "
        "AND NOT EXISTS (SELECT 1 FROM client_invitations WHERE client_id = clients.id) "
        "AND NOT EXISTS (SELECT 1 FROM plans WHERE profile_id = clients.id)"
    )
    owner = (client_id, g.user["id"])

    if request.method == "POST":
        check_csrf()
        with g.db:
            result = g.db.execute(
                f"DELETE FROM clients WHERE id = ? AND trainer_id = ? AND {unused_profile}",
                owner,
            )
        if result.rowcount:
            return redirect(url_for("clients.index"))
        return render_template("client_delete.html", profile=profile, can_delete=False), 409

    can_delete = g.db.execute(
        f"SELECT 1 FROM clients WHERE id = ? AND trainer_id = ? AND {unused_profile}",
        owner,
    ).fetchone()
    return render_template("client_delete.html", profile=profile, can_delete=can_delete)


@bp.route("/clients/<int:client_id>/invite", methods=["GET", "POST"])
def invite(client_id):
    get_visible_client(client_id)
    if request.method == "GET":
        return redirect(url_for("clients.manage_invitations", profile_id=client_id))
    return manage_invitations(client_id)


@bp.route("/clients/invitations", methods=["GET", "POST"])
def manage_invitations(client_id=None):
    trainer_id = g.user["id"]
    form = request.form if request.method == "POST" else request.args
    selected_profile = str(client_id) if client_id is not None else form.get("profile_id", "")
    error = None

    if request.method == "POST":
        check_csrf()
        email = request.form.get("email", "").strip().lower()
        with g.db:
            g.db.execute("BEGIN IMMEDIATE")
            recipient = g.db.execute(
                "SELECT id, name FROM users WHERE email = ? AND role = 'client'", (email,)
            ).fetchone()
            profile = None
            if selected_profile:
                try:
                    profile_id = int(selected_profile)
                except ValueError:
                    abort(404)
                if not 0 < profile_id < 2**63:
                    abort(404)
                profile = get_visible_client(profile_id)

            if recipient is None:
                error = "Enter the email address of a registered client."
            elif profile is not None and profile["client_user_id"] is not None:
                error = "This profile is already linked."
            elif g.db.execute(
                "SELECT 1 FROM clients WHERE client_user_id = ?", (recipient["id"],)
            ).fetchone():
                error = "This client account is already linked."
            elif g.db.execute(
                "SELECT 1 FROM client_invitations AS i JOIN clients AS c ON c.id = i.client_id "
                "WHERE c.trainer_id = ? AND i.client_user_id = ? AND i.status = 'pending'",
                (trainer_id, recipient["id"]),
            ).fetchone():
                error = "You already have a pending invitation for this client."
            elif profile is not None and g.db.execute(
                "SELECT 1 FROM client_invitations WHERE client_id = ? AND status = 'pending'",
                (profile["id"],),
            ).fetchone():
                error = "This profile already has a pending invitation."
            else:
                if profile is None:
                    profile_id = g.db.execute(
                        "INSERT INTO clients (name, trainer_id) VALUES (?, ?)",
                        (recipient["name"], trainer_id),
                    ).lastrowid
                g.db.execute(
                    "INSERT INTO client_invitations (client_id, client_user_id) VALUES (?, ?)",
                    (profile_id, recipient["id"]),
                )
        if error is None:
            return redirect(url_for("clients.manage_invitations"))

    profiles = g.db.execute(
        "SELECT c.id, c.name FROM clients AS c WHERE c.trainer_id = ? AND c.client_user_id IS NULL "
        "AND NOT EXISTS (SELECT 1 FROM client_invitations AS i WHERE i.client_id = c.id AND i.status = 'pending') "
        "ORDER BY c.name, c.id",
        (trainer_id,),
    ).fetchall()
    invitations = g.db.execute(
        "SELECT c.name AS profile_name, u.email, i.status FROM client_invitations AS i "
        "JOIN users AS u ON u.id = i.client_user_id JOIN clients AS c ON c.id = i.client_id "
        "WHERE c.trainer_id = ? ORDER BY i.id DESC",
        (trainer_id,),
    ).fetchall()
    return render_template(
        "invite_client.html", profiles=profiles, selected_profile=selected_profile,
        invitations=invitations, error=error,
    ), 400 if error else 200


def get_linked_profile():
    return g.db.execute(
        "SELECT c.id, c.name, c.goals, u.name AS trainer_name "
        "FROM clients AS c JOIN users AS u ON u.id = c.trainer_id "
        "WHERE c.client_user_id = ?",
        (g.user["id"],),
    ).fetchone()


@bp.get("/invitations")
def invitations():
    pending = g.db.execute(
        "SELECT i.id, c.name AS profile_name, u.name AS trainer_name "
        "FROM client_invitations AS i JOIN clients AS c ON c.id = i.client_id "
        "JOIN users AS u ON u.id = c.trainer_id "
        "WHERE i.client_user_id = ? AND i.status = 'pending' ORDER BY i.id DESC",
        (g.user["id"],),
    ).fetchall()
    return render_template("invitations.html", invitations=pending, profile=get_linked_profile())


@bp.post("/invitations/<int:invitation_id>/respond")
def respond(invitation_id):
    check_csrf()
    decision = request.form.get("decision")
    if decision not in ("accept", "decline"):
        abort(400)

    user_id = g.user["id"]
    with g.db:
        g.db.execute("BEGIN IMMEDIATE")
        invitation = g.db.execute(
            "SELECT client_id, status FROM client_invitations WHERE id = ? AND client_user_id = ?",
            (invitation_id, user_id),
        ).fetchone()
        if invitation is None:
            abort(404)
        if invitation["status"] != "pending":
            abort(409)

        if decision == "accept":
            updated = g.db.execute(
                "UPDATE clients SET client_user_id = ? "
                "WHERE id = ? AND client_user_id IS NULL AND trainer_id IS NOT NULL "
                "AND NOT EXISTS (SELECT 1 FROM clients WHERE client_user_id = ?)",
                (user_id, invitation["client_id"], user_id),
            )
            if not updated.rowcount:
                abort(409)
            g.db.execute(
                "UPDATE client_invitations SET status = 'declined' "
                "WHERE client_user_id = ? AND status = 'pending' AND id != ?",
                (user_id, invitation_id),
            )
        g.db.execute(
            "UPDATE client_invitations SET status = ? WHERE id = ?",
            ("accepted" if decision == "accept" else "declined", invitation_id),
        )
    return redirect(url_for("clients.invitations"))
