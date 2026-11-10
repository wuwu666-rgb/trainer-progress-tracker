# Free HTTPS deployment

Public HTTPS deployment is deferred for this release. Keep this guide for a future release.

Use a PythonAnywhere free account and its provided subdomain. The web app runs on PythonAnywhere while your computer is off. The free web app expires after one month unless renewed from the dashboard.

## First deploy

In a PythonAnywhere Bash console, run the following after these changes are on GitHub `main`.

```bash
git clone --branch main https://github.com/wuwu666-rgb/trainer-progress-tracker.git ~/repbook
python3.13 -m venv ~/.virtualenvs/repbook
~/.virtualenvs/repbook/bin/python -m pip install -r ~/repbook/requirements.txt
mkdir -m 700 ~/repbook-data
(umask 077; python3.13 -c 'import secrets; print(secrets.token_hex(32))' > ~/repbook-data/session-secret)
```

Run the secret generation step once. Keep the data directory outside the Git checkout so a code update does not replace the database or session key.

In **Web**, add a web app using **Manual configuration** and Python 3.13. Set its virtualenv to `/home/YOUR_USERNAME/.virtualenvs/repbook`. Replace the generated WSGI file with this configuration.

```python
import os
import sys

sys.path.insert(0, "/home/YOUR_USERNAME/repbook")
os.environ["REPBOOK_DATA_DIR"] = "/home/YOUR_USERNAME/repbook-data"
from wsgi import application
```

Enable **Force HTTPS**, click **Reload**, and open the HTTPS URL shown in **Web**. On first startup OneTrainer creates empty tables. Users register on the deployed site.

## Publish updates and verify persistence

After changes land on GitHub `main`, pull them on PythonAnywhere, update dependencies, and click **Reload** in **Web**.

```bash
git -C ~/repbook pull --ff-only origin main
~/.virtualenvs/repbook/bin/python -m pip install -r ~/repbook/requirements.txt
```

To verify task 10.1, create a test account and save a test training record through the public HTTPS site. Reload the service from the dashboard and check that the same account can still sign in and view that record at the same URL.
