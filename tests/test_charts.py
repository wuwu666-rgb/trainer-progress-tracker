import json
import re
import sqlite3
import tempfile
import unittest
from pathlib import Path

from werkzeug.security import generate_password_hash

import app as app_module
from history import get_body_weight_series, get_exercise_series


class ChartTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        app_module.app.config.update(DATABASE=Path(self.tmp.name) / "test.sqlite3", TESTING=True)
        app_module.init_database()
        self.db = sqlite3.connect(app_module.app.config["DATABASE"])
        with self.db:
            # Trainer 1 coaches client user 3 (profile 1); trainer 2 coaches client user 4 (profile 2).
            for uid, role in ((1, "trainer"), (2, "trainer"), (3, "client"), (4, "client")):
                self.db.execute(
                    "INSERT INTO users (id, name, email, password_hash, role) VALUES (?, ?, ?, ?, ?)",
                    (uid, f"U{uid}", f"{uid}@example.com", generate_password_hash("pw"), role),
                )
            self.db.execute("INSERT INTO clients (id, name, trainer_id, client_user_id) VALUES (1, 'A', 1, 3)")
            self.db.execute("INSERT INTO clients (id, name, trainer_id, client_user_id) VALUES (2, 'B', 2, 4)")
        self.client = app_module.app.test_client()

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def login(self, user_id):
        with self.client.session_transaction() as session:
            session["user_id"] = user_id
            session["csrf_token"] = "token"

    def session_workout(self, workout_id, client_id, day, exercise, unit, sets, completed=True):
        with self.db:
            self.db.execute(
                "INSERT INTO workout_sessions (id, client_id, recorder_id, workout_date, completed_at) "
                "VALUES (?, ?, 1, ?, ?)", (workout_id, client_id, day, "2024-01-01" if completed else None),
            )
            exercise_id = self.db.execute(
                "INSERT INTO workout_session_exercises (workout_id, position, name, unit) VALUES (?, 1, ?, ?)",
                (workout_id, exercise, unit),
            ).lastrowid
            for position, (result, weight) in enumerate(sets, 1):
                self.db.execute(
                    "INSERT INTO workout_session_sets (exercise_id, position, result, weight_lb) VALUES (?, ?, ?, ?)",
                    (exercise_id, position, result, weight),
                )

    def series(self, function, client_id):
        with app_module.app.test_request_context():
            from flask import g
            g.db = sqlite3.connect(app_module.app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
            try:
                return function(client_id)
            finally:
                g.db.close()

    def test_body_weight_is_sorted_and_skips_bad_values(self):
        with self.db:
            for day, weight in (("2024-03-02", "181.5"), ("2024-03-01", "180"), ("2024-03-03", "oops"), ("2024-03-04", "0")):
                self.db.execute(
                    "INSERT INTO body_weights (client_id, recorded_by, measurement_date, weight_lb) VALUES (1, 1, ?, ?)",
                    (day, weight),
                )
        points = self.series(get_body_weight_series, 1)
        self.assertEqual(points, [{"date": "2024-03-01", "value": 180.0}, {"date": "2024-03-02", "value": 181.5}])

    def test_reps_chart_top_weight_per_day_ignoring_blank_weights(self):
        self.session_workout(1, 1, "2024-03-01", "Squat", "reps", [("5", "100"), ("5", "110"), ("5", None)])
        self.session_workout(2, 1, "2024-03-08", "squat ", "reps", [("5", "120")])
        self.session_workout(3, 1, "2024-03-09", "Push-up", "reps", [("20", None)])
        (series,) = self.series(get_exercise_series, 1)
        self.assertEqual(series["name"], "Squat")
        self.assertEqual(series["points"], [{"date": "2024-03-01", "value": 110.0}, {"date": "2024-03-08", "value": 120.0}])

    def test_timed_exercises_sum_minutes_per_day(self):
        self.session_workout(1, 1, "2024-03-01", "Jog", "minutes", [("10", None), ("15.5", None)])
        self.session_workout(2, 1, "2024-03-02", "Jog", "minutes", [("20", None)])
        (series,) = self.series(get_exercise_series, 1)
        self.assertEqual(series["unit"], "minutes")
        self.assertEqual([point["value"] for point in series["points"]], [25.5, 20.0])

    def test_drafts_and_single_day_exercises_are_left_out(self):
        self.session_workout(1, 1, "2024-03-01", "Squat", "reps", [("5", "100")], completed=False)
        self.session_workout(2, 1, "2024-03-02", "Squat", "reps", [("5", "100")])
        self.assertEqual(self.series(get_exercise_series, 1), [])

    def test_older_records_are_included(self):
        with self.db:
            self.db.execute("INSERT INTO workouts (client_id, workout_date, exercise, reps, weight_lb) VALUES (1, '2024-01-01', 'Bench', 5, '95')")
            self.db.execute("INSERT INTO workouts (client_id, workout_date, exercise, reps, weight_lb) VALUES (1, '2024-01-08', 'bench', 5, '100')")
        (series,) = self.series(get_exercise_series, 1)
        self.assertEqual([point["value"] for point in series["points"]], [95.0, 100.0])

    def test_same_name_in_two_units_is_labelled(self):
        self.session_workout(1, 1, "2024-03-01", "Row", "reps", [("5", "50")])
        self.session_workout(2, 1, "2024-03-02", "Row", "reps", [("5", "55")])
        self.session_workout(3, 1, "2024-03-03", "Row", "minutes", [("10", None)])
        self.session_workout(4, 1, "2024-03-04", "Row", "minutes", [("12", None)])
        self.assertEqual(sorted(item["label"] for item in self.series(get_exercise_series, 1)), ["Row (minutes)", "Row (reps)"])

    def embedded(self, response):
        match = re.search(r'id="chart-data">(.*?)</script>', response.get_data(as_text=True), re.S)
        return json.loads(match.group(1))

    def test_client_progress_page_shows_only_their_data(self):
        self.session_workout(1, 1, "2024-03-01", "Squat", "reps", [("5", "100")])
        self.session_workout(2, 1, "2024-03-08", "Squat", "reps", [("5", "110")])
        self.session_workout(3, 2, "2024-03-01", "Deadlift", "reps", [("5", "200")])
        self.session_workout(4, 2, "2024-03-08", "Deadlift", "reps", [("5", "210")])
        self.login(3)
        response = self.client.get("/dashboard/progress")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["name"] for item in self.embedded(response)["exercises"]], ["Squat"])

    def test_trainer_sees_own_client_and_not_another_trainers(self):
        self.login(1)
        self.assertEqual(self.client.get("/clients/1/history").status_code, 200)
        self.assertEqual(self.client.get("/clients/2/history").status_code, 404)

    def test_page_cannot_be_broken_by_script_in_exercise_name(self):
        for number, day in enumerate(("2024-03-01", "2024-03-02"), 1):
            self.session_workout(number, 1, day, "</script><b>x", "reps", [("5", "100")])
        self.login(3)
        body = self.client.get("/dashboard/progress").get_data(as_text=True)
        self.assertNotIn("</script><b>", body)
        self.assertEqual(self.embedded(self.client.get("/dashboard/progress"))["exercises"][0]["name"], "</script><b>x")


if __name__ == "__main__":
    unittest.main()
