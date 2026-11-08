import os
from pathlib import Path

from app import app, init_database

data_dir = Path(os.environ["REPBOOK_DATA_DIR"]).resolve()
secret = (data_dir / "session-secret").read_text(encoding="ascii").strip()
if len(secret) < 32:
    raise RuntimeError("Generate a random session-secret in the Repbook data directory.")

app.config.update(
    DATABASE=data_dir / "trainer.sqlite3",
    SECRET_KEY=secret,
    SESSION_COOKIE_SECURE=True,
)
init_database(seed_demo=False)
application = app
