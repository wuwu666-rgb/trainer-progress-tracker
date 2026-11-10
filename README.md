# OneTrainer

OneTrainer is a mobile-friendly workout tracker for trainers and clients.

- Trainers manage client profiles, assign plans from reusable templates or from scratch, and record workouts and body-weight measurements.
- Clients follow assigned workouts one set at a time and can resume saved drafts. Completed workouts move from **My workouts** to **Progress**, where clients can also view their body-weight history.
- Each client can connect to one trainer at a time. Either person can end the connection from **Account**. Clients keep their completed workout and body-weight history. Former and new trainers cannot access records from the ended connection.

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

Keep the terminal running and open [OneTrainer](http://127.0.0.1:5000/login). If you started Flask on another port, use the address shown in the terminal. After the initial setup, rerun only the last command to start the app.

## Local demo accounts

Starting `app.py` creates these demo accounts in the local database.

| Role | Email | Password |
| --- | --- | --- |
| Trainer | `demo-trainer-84d617@example.com` | `JsL_iMYZv-B1aFeo` |
| Client | `demo-client-2c4784@example.com` | `T0Pujje4zsgrNaDL` |

These public credentials are for local demos. Each checkout uses its own `trainer.sqlite3` database. Restarting the app preserves saved records and applies supported database upgrades.

## Try the trainer-to-client flow

1. Sign in as the demo trainer. Go to **Clients → Invitations**, enter the demo client’s email, and send an invitation. Create a profile during the invitation or choose an existing unlinked profile.
2. Sign in as the demo client. Open **Invitations** from the home page and accept the invitation.
3. Sign back in as the trainer. From **Clients**, select **Plan workout** on the linked client’s card. Use a saved template or start from scratch. Choose **Reps** or **Minutes** for each exercise. For example, set jogging to one set of 20 minutes. Assign the plan to the client. Later template edits leave the assigned plan intact.
4. Sign in as the client. Open **Workouts**, choose the assigned plan, and select **Start workout**. Enter the result for each set and move to the next set or exercise. Use **Save draft** to resume later, or choose **Review workout → Save workout** and confirm to finish.
5. In the client’s **Progress**, open the completed workout to see each set. The trainer can see the same results from **Clients → View history** and open **Body-weight history** there to record or correct a measurement.

## Install on a phone

Open the site over HTTPS, sign in, and choose **Account → Install OneTrainer**. Confirm the browser’s install prompt if it appears. On iPhone, open the site in Safari and choose **Share → Add to Home Screen**. Turn on **Open as Web App** if shown, then tap **Add**.

Signing in, starting a workout, and viewing history require an internet connection. A workout you already opened can be recorded offline: entries are kept on the device, and **Save draft** or **Save workout** are queued and sync when you reconnect. If the workout changed elsewhere in the meantime, your entries stay on the device and you choose whether to use or discard them. Offline recording needs HTTPS (or `localhost`) and is best-effort, because a browser can clear its stored data, so reconnect soon after recording. Run the tests with `python -m unittest discover -s tests -t .`.

## Share a temporary preview with GitHub Codespaces

### First-time setup

1. On GitHub, choose **Code → Codespaces → Create codespace on main**. Open its terminal and run:

   ```bash
   python3 -m venv .venv
   ./.venv/bin/python -m pip install -r requirements.txt waitress
   export REPBOOK_DATA_DIR="$HOME/repbook-preview-data"
   mkdir -p -m 700 "$REPBOOK_DATA_DIR"
   if [ ! -s "$REPBOOK_DATA_DIR/session-secret" ]; then
     (umask 077; ./.venv/bin/python -c 'import secrets; print(secrets.token_hex(32))' > "$REPBOOK_DATA_DIR/session-secret")
   fi
   ./.venv/bin/waitress-serve --listen=127.0.0.1:5000 wsgi:application
   ```

2. Open the **Ports** panel. If port **5000** is missing, choose **Forward a Port** and enter `5000`. Right-click that port and choose **Port Visibility → Public**.
3. Copy the forwarded HTTPS address and share it with your teammates. The preview starts with an empty database. Teammates can open the link on a phone or computer and register test accounts.

### Restart an existing preview

If the Codespace stops, reopen the same Codespace and run:

```bash
export REPBOOK_DATA_DIR="$HOME/repbook-preview-data"
./.venv/bin/waitress-serve --listen=127.0.0.1:5000 wsgi:application
```

The same Codespace keeps its test database. Check that port **5000** is **Public** before sharing the HTTPS address again. [GitHub port forwarding guide](https://docs.github.com/en/codespaces/developing-in-a-codespace/forwarding-ports-in-your-codespace)

## Project status

Public HTTPS deployment is deferred for this release. Offline recording of an already-opened workout is available; starting workouts and browsing history offline are not.

See [Issue #1](https://github.com/wuwu666-rgb/trainer-progress-tracker/issues/1) for task ownership and completion status.
