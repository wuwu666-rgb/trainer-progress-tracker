import csv
import io
import unittest
from datetime import date, timedelta

from tests import test_charts


class ExportTests(unittest.TestCase):
    setUp = test_charts.ChartTests.setUp
    tearDown = test_charts.ChartTests.tearDown
    login = test_charts.ChartTests.login
    session_workout = test_charts.ChartTests.session_workout

    def download(self, path="/dashboard/progress/export.csv"):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        return response, list(csv.DictReader(io.StringIO(response.get_data(as_text=True))))

    def test_sets_legacy_records_drafts_and_response_headers(self):
        self.session_workout(1, 1, "2024-03-02", 'Squat, "重"\nbar', "reps", [("5", "100"), ("4", None)])
        self.session_workout(2, 1, "2024-03-03", "Jog", "minutes", [("12.50", None)])
        self.session_workout(3, 1, "2024-03-04", "Draft", "reps", [("5", "50")], completed=False)
        self.session_workout(4, 2, "2024-03-01", "Private", "reps", [("5", "50")])
        with self.db:
            self.db.execute("INSERT INTO workouts (client_id, workout_date, exercise, reps, weight_lb, set_count) VALUES (1, '2024-03-01', 'Push-up', 10, '0', 2)")
            self.db.execute("INSERT INTO cardio_workouts (client_id, workout_date, exercise, duration_min, distance_km, set_count) VALUES (1, '2024-03-01', 'Walk', '5.5', '0.4', 2)")
        before = list(self.db.iterdump())
        self.login(3)
        response, rows = self.download()
        self.assertEqual(len(rows), 7)
        self.assertEqual([r["exercise"] for r in rows], ["Push-up"] * 2 + ["Walk"] * 2 + ['Squat, "重"\nbar'] * 2 + ["Jog"])
        self.assertEqual([r["set_number"] for r in rows], ["1", "2", "1", "2", "1", "2", "1"])
        self.assertEqual(rows[0]["recorder_name"], "")
        self.assertEqual(rows[2]["distance_km"], "0.4")
        self.assertEqual(rows[4]["recorder_name"], "U1")
        self.assertEqual(rows[4]["recorder_role"], "trainer")
        self.assertEqual(rows[5]["weight_lb"], "")
        self.assertEqual(rows[6]["minutes"], "12.50")
        self.assertEqual(rows[6]["reps"], "")
        self.assertEqual(response.headers["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn('filename="training-history.csv"', response.headers["Content-Disposition"])
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(before, list(self.db.iterdump()))

    def test_body_weights_are_complete_and_preserve_precision(self):
        with self.db:
            for number in range(105):
                self.db.execute(
                    "INSERT INTO body_weights (client_id, recorded_by, measurement_date, weight_lb) VALUES (1, 1, ?, '180.125')",
                    ((date(2024, 1, 1) + timedelta(days=number)).isoformat(),),
                )
            self.db.execute("INSERT INTO body_weights (client_id, recorded_by, measurement_date, weight_lb) VALUES (2, 2, '2024-01-01', '999')")
        self.login(3)
        response, rows = self.download("/dashboard/progress/export.csv?kind=body-weight")
        self.assertEqual(len(rows), 105)
        self.assertEqual(rows[0], {"date": "2024-01-01", "weight_lb": "180.125", "recorder_name": "U1", "recorder_role": "trainer"})
        self.assertLess(rows[0]["date"], rows[-1]["date"])
        self.assertIn('filename="body-weight-history.csv"', response.headers["Content-Disposition"])

    def test_formula_text_is_neutralized(self):
        names = ["=1+1", " +SUM(1)", "-1+1", "@SUM(1)", "\ttext", "\rtext", "\ntext", " \t=1"]
        for number, name in enumerate(names, 1):
            self.session_workout(number, 1, "2024-03-01", name, "reps", [("5", "100")])
        with self.db:
            self.db.execute("UPDATE users SET name = '=FORMULA' WHERE id = 1")
        self.login(3)
        _, rows = self.download()
        self.assertEqual([r["exercise"] for r in rows], ["'" + name for name in names])
        self.assertTrue(all(r["recorder_name"] == "'=FORMULA" for r in rows))

    def test_access_checks_for_both_export_kinds(self):
        for suffix in ("", "?kind=body-weight"):
            self.assertEqual(self.client.get("/dashboard/progress/export.csv" + suffix).status_code, 302)
        for uid, allowed, forbidden in ((1, 1, 2), (2, 2, 1), (3, 1, 2), (4, 2, 1)):
            self.login(uid)
            for suffix in ("", "?kind=body-weight"):
                self.download(f"/clients/{allowed}/history/export.csv{suffix}")
                self.assertEqual(self.client.get(f"/clients/{forbidden}/history/export.csv{suffix}").status_code, 404)
        self.login(1)
        self.assertEqual(self.client.get("/dashboard/progress/export.csv").status_code, 404)
        self.assertEqual(self.client.get("/clients/99999999999999999999999/history/export.csv").status_code, 404)
        self.login(3)
        self.assertEqual(self.client.get("/dashboard/progress/export.csv?kind=unknown").status_code, 404)

    def test_disconnected_history_stays_with_client(self):
        self.session_workout(1, 1, "2024-03-01", "Old squat", "reps", [("5", "100")])
        with self.db:
            self.db.execute("UPDATE clients SET archived_client_user_id = client_user_id, client_user_id = NULL, trainer_id = NULL WHERE id = 1")
            self.db.execute("INSERT INTO clients (id, name, trainer_id, client_user_id) VALUES (3, 'New profile', 2, 3)")
        self.login(3)
        _, rows = self.download()
        self.assertEqual(rows[0]["exercise"], "Old squat")
        self.download("/clients/1/history/export.csv")
        for uid in (1, 2):
            self.login(uid)
            for suffix in ("", "?kind=body-weight"):
                self.assertEqual(self.client.get("/clients/1/history/export.csv" + suffix).status_code, 404)

    def test_empty_files_and_page_links(self):
        self.login(3)
        for suffix in ("", "?kind=body-weight"):
            _, rows = self.download("/dashboard/progress/export.csv" + suffix)
            self.assertEqual(rows, [])
        body = self.client.get("/dashboard/progress").get_data(as_text=True)
        self.assertIn('/dashboard/progress/export.csv', body)
        self.assertIn('kind=body-weight', body)
        self.login(1)
        body = self.client.get("/clients/1/history").get_data(as_text=True)
        self.assertIn('/clients/1/history/export.csv', body)
        self.assertIn('Download CSV', body)


if __name__ == "__main__":
    unittest.main()
