# Repbook

Repbook is a mobile-friendly workout tracker for trainers and clients. Trainers manage client profiles, create reusable templates, assign workout plans, and record training. Clients can accept trainer invitations, see assigned workouts, and review saved training in **Progress**.

## Run locally

Install Python 3.10 or newer, clone this repository, and open its root folder in VS Code or a terminal.

### Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

If your Python installation provides `python` instead of `py`, run `python -m venv .venv` for the first step.

### macOS or Linux

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python app.py
```

Keep the terminal running and open [Repbook](http://127.0.0.1:5000/login) in your browser. Use the address printed by Flask if you started it on another port. After the initial setup, rerun only the last command to start the app again.

## Local demo accounts

Starting `app.py` creates these demo accounts in your local database.

| Role | Email | Password |
| --- | --- | --- |
| Trainer | `demo-trainer-84d617@example.com` | `JsL_iMYZv-B1aFeo` |
| Client | `demo-client-2c4784@example.com` | `T0Pujje4zsgrNaDL` |

These public credentials are for local demos with sample data. Each checkout uses its own `trainer.sqlite3` database. Saved records persist between restarts, and startup applies supported database upgrades.

## Try the trainer-to-client flow

1. Sign in as the **Demo Trainer**. Go to **Clients → Invitations**, enter the Demo Client email, and send an invitation. You can create a profile as part of the invitation or select an existing unlinked profile.
2. Sign in as the **Demo Client**. Open **Invitations** from the homepage and accept the invitation.
3. Sign back in as the trainer. In **Plans**, choose **Create plan from scratch** or use **Create plan from template** on a saved template. Assign the plan to the linked client. Later template edits leave previously copied plans intact.
4. From **Clients**, choose **Record training** on that client’s card. Save a strength record with reps and weight, or a cardio record with duration and optional distance.
5. Sign in as the client. **Workouts** shows assigned plans. **Progress** shows saved training records.

## Project status

The public HTTPS deployment is pending. GitHub hosts the source code, and the link above opens a local development server on your computer.

The current recorder saves one exercise entry at a time. Full multi-exercise sessions, independent client recording, corrections, and body-weight tracking are still planned. Offline recording, recovery, and synchronization are deferred.

See [Issue #1](https://github.com/wuwu666-rgb/trainer-progress-tracker/issues/1) for task ownership and completion status.
