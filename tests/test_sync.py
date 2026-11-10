import sqlite3
import tempfile
import unittest
from pathlib import Path

from werkzeug.security import generate_password_hash

import app as app_module


class SyncEndpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        app_module.app.config.update(DATABASE=Path(self.tmp.name) / "test.sqlite3", TESTING=True)
        app_module.init_database()
        db = sqlite3.connect(app_module.app.config["DATABASE"])
        with db:
            for uid, role in ((1, "trainer"), (2, "client"), (3, "client")):
                db.execute(
                    "INSERT INTO users (id, name, email, password_hash, role) VALUES (?, ?, ?, ?, ?)",
                    (uid, role.title(), f"{uid}@example.com", generate_password_hash("pw"), role),
                )
            db.execute("INSERT INTO clients (id, name, trainer_id, client_user_id) VALUES (1, 'C', 1, 2)")
            db.execute(
                "INSERT INTO workout_sessions (id, client_id, recorder_id, plan_name, workout_date) "
                "VALUES (1, 1, 2, 'Plan', '2020-01-01')"
            )
            db.execute(
                "INSERT INTO workout_session_exercises (id, workout_id, position, name, unit, target_sets, target_reps) "
                "VALUES (10, 1, 1, 'Squat', 'reps', 3, 5)"
            )
        db.close()
        self.client = app_module.app.test_client()
        self.login(2)

    def tearDown(self):
        self.tmp.cleanup()

    def login(self, user_id, client=None):
        with (client or self.client).session_transaction() as session:
            session["user_id"] = user_id
            session["csrf_token"] = "token"

    def post(self, data=None, workout_id=1, client=None, headers=None):
        base = {"revision": "0", "action": "save", "exercise_key": "10",
                "result_10": ["5", "5"], "weight_10": ["100", ""]}
        base.update(data or {})
        return (client or self.client).post(
            f"/workouts/{workout_id}/sync", data=base,
            headers={"X-CSRF-Token": "token", **(headers or {})},
        )

    def test_saves_draft_and_returns_new_revision(self):
        response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["state"], "ok")
        self.assertEqual(response.get_json()["revision"], 1)
        self.assertFalse(response.get_json()["complete"])

    def test_complete_marks_workout_finished(self):
        response = self.post({"action": "complete"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["complete"])
        self.assertEqual(self.post({"action": "complete", "revision": "1"}).status_code, 409)

    def test_stale_revision_is_a_conflict_and_changes_nothing(self):
        self.assertEqual(self.post().status_code, 200)
        response = self.post()  # still revision 0
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["state"], "conflict")

    def test_invalid_results_are_rejected(self):
        response = self.post({"result_10": ["-3"]})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["state"], "invalid")

    def test_missing_csrf_is_rejected(self):
        response = self.client.post("/workouts/1/sync", data={"revision": "0", "action": "save"})
        self.assertEqual(response.status_code, 400)

    def test_other_users_workout_is_hidden(self):
        other = app_module.app.test_client()
        self.login(3, other)
        self.assertEqual(self.post(client=other).status_code, 404)

    def test_rejects_unknown_action(self):
        self.assertEqual(self.post({"action": "discard"}).status_code, 400)


if __name__ == "__main__":
    unittest.main()
