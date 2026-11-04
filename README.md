# Repbook

Runnable Flask and SQLite starter for the team. Use sample data on localhost. The starter has no authentication or access controls.

## Run locally

With Python 3.10 or newer installed:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Open http://127.0.0.1:5000. Choose **Clients → Sample Client → Record training**, save one set, and verify it appears under **Training history**. The first start creates `trainer.sqlite3`. Saved records persist between restarts.

## Team handoff

| Slice | Starting files | Next work |
| --- | --- | --- |
| Accounts and clients | `clients.py`, `templates/clients.html` | Registration, login, client profile editing, invitations, and shared server-side access checks. Add an `auth.py` blueprint. |
| Planning and templates | `planning.py`, `templates/planning.html` | Template editing, individual workout plans, and client assignments. |
| Workout recording | `sessions.py`, `templates/record.html` | Multiple exercises and sets per session, coach-led and independent sessions, past workout entry and corrections. |
| History and body weight | `history.py`, `templates/history.html` | History details, body-weight records, and deployment. |

The SQLite schema is for the demo flow. Before changing shared tables, agree on the data model and route contracts from the Project Plan, especially how plans, sessions, and set results relate. Coordinate shared changes to `app.py`, `schema.sql`, and `templates/base.html` across slices. SQLite's `CREATE TABLE IF NOT EXISTS` does not migrate an existing database. Agree on a migration strategy as the shared schema evolves.

## Deferred scope

Offline recording, recovery, and synchronization are deferred. The current release uses the Flask server and SQLite for saving and reading records.
