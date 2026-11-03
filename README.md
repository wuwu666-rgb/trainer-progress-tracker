# RepFlow

A mobile-friendly workout tracker that brings personal trainers, clients, workout plans, and session records into one purple-themed workspace.

**Status:** functional local MVP under development. Real-device offline acceptance and production deployment are still pending.

## Technology

| Layer | Technology |
| --- | --- |
| Interface | HTML, CSS, vanilla JavaScript; English UI |
| Backend | Python / Flask |
| Database | SQLite |
| Device storage | IndexedDB |
| Offline shell | Service Worker and web manifest |

## Features by slice

### 1. Accounts and client profiles

- Register as a personal trainer or client; sign in and sign out.
- Password hashing, signed sessions, CSRF tokens, and server-side authorization.
- Trainers create and update client profiles and goals.
- Invite an already registered client by email; clients accept or decline.
- Each linked client can have one trainer.

### 2. Workout planning and templates

- Create and edit reusable workout templates.
- Define exercise order and target sets/reps.
- Assign copied plans to clients or create individual workouts.
- Template edits do not rewrite existing assignments.

### 3. Session recording and corrections

- Prepare assigned workouts online for independent client recording.
- Trainers can start blank sessions, add exercises, and enter past workouts.
- Record actual reps and weight in pounds for each set.
- Save drafts locally, resume recording, and complete sessions.
- Only the original recorder on the recording device can correct a session; corrections require an online save.

### 4. History, body weight, and offline support

- View completed workout history and detailed results.
- Trainers enter and correct dated body-weight measurements.
- Store account-scoped snapshots, session drafts, and pending uploads in IndexedDB.
- Cache public application assets for offline reopening after initial online preparation.
- Retry pending uploads when the app returns online.
- Use operation receipts and version/device checks to reject duplicate or conflicting writes.

## Getting started

Requires Python 3.10+ and pip. Python 3.12 is used in the current development environment.

```bash
python -m venv .venv
```

Activate the environment:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, you can use the environment directly without changing execution policies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

On macOS/Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:8080**. The server creates a local SQLite database and signing key on first use. There are no seeded accounts.

On Windows, `start.cmd` uses `.venv` when available and otherwise falls back to `python`. Create the virtual environment and install dependencies before starting.

## Try the trainer-to-client workflow

1. Register a trainer account.
2. Register a client account in a different browser or private browsing window.
3. As trainer, add a client profile and invite the client's registered email.
4. As client, open **Invitations** and accept.
5. As trainer, create a template and choose **Assign workout**.
6. As client, open **Workouts**, choose **Prepare & start**, and record sets.
7. Choose **Complete workout**, then review **History**.
8. As trainer, add a measurement in **Body weight**.

## Offline workflow

Prepare a workout while online on the device that will record it. Keep that account signed in. Input drafts save after a short pause; use **Save on this device** to persist a session revision and queue its upload. Previously cached application assets and prepared data support offline use. Reconnect with the app open to retry pending uploads.

A pending revision must sync before another revision for the same session can be queued. Sign-out is blocked while uploads are pending. Do not edit the same session in multiple tabs.

## Validation

```bash
python -m unittest test_app.py
node --check static/app.js
```

Node is optional for running the app; it is only needed for the JavaScript syntax check. The integration test uses an isolated temporary database and covers account registration, invitation acceptance, workout assignment and completion, idempotent retries, recorder permissions, stale versions, and missing CSRF protection. These checks do not establish real-device offline compatibility.

## Project structure

```text
app.py                 Flask API, authorization, validation, SQLite persistence
static/index.html      Application shell
static/style.css       Purple responsive interface
static/app.js          Screens, forms, recorder, local storage, upload queue
static/sw.js           Public application-shell caching
static/manifest.json   Web application metadata
requirements.txt       Python dependencies
test_app.py            Core workflow integration test
start.cmd              Windows launcher
start.ps1              Alternative PowerShell launcher
```

The API uses same-origin `/api` endpoints. JSON responses contain `data` on success or `error` on failure. The current implementation stores feature records as JSON in SQLite rather than the fully normalized schema proposed in the project plan.

## Milestones and remaining work

| Milestone | Current state | Remaining acceptance |
| --- | --- | --- |
| M1: setup and offline prototype | Local Flask/SQLite and offline storage implemented | Phone close/reopen tests; hosting selection |
| M2: accounts and connections | Core flow covered by integration test | Broader permission and sign-out scenarios |
| M3: planning and recording | Templates, assignments, recording and past entry implemented | Dedicated step-by-step recorder; broader browser interaction tests |
| M4: history and synchronization | History, weights, drafts and upload queue implemented | Two-tab leases, concurrent queue protection, conflict recovery and real-device offline tests |
| M5: deployment and demonstration | Local development only | HTTPS hosting, persistent storage, backups/restart checks, iPhone Safari and Android Chrome acceptance |

Progress comparison and history filters (F8/F9) are outside the planned MVP scope. The implementation is not yet a fully accepted production release.

## Deployment notes

Use a production WSGI server behind HTTPS. Set `HTTPS=1` to enable Secure session cookies and configure a stable `SECRET_KEY` or preserve the generated `.secret`. Keep `tracker.sqlite3` on persistent storage and back it up. `PORT` changes the default port (8080). Offline Service Workers require HTTPS outside localhost.

The Flask development server is for local use. GitHub stores the source code; GitHub Pages cannot run this Flask backend or persist SQLite.

## Local data and secrets

`.gitignore` excludes signing keys, databases, environment files, dependencies, logs, screenshots, and test temporary directories. No account passwords, client records, or local signing keys should be committed.
