from datetime import datetime
from tests.base import AppTestCase

YEAR = datetime.now().year


class TransactionTests(AppTestCase):
    def setUp(self):
        super().setUp()
        self.create_verified_user("me@vsteschenko.me")
        self.login("me@vsteschenko.me")

    def add(self, **overrides):
        data = {"type": "expense", "expense-category": "grocery", "place": "shop",
                "tx_time": "10:00", "comment": "", "amount": "5"}
        data.update(overrides)
        return self.client.post(f"/?year={YEAR}&month=3&day=4", data=data)

    def test_valid_transactions_are_saved(self):
        self.assertEqual(self.add().status_code, 302)
        self.assertEqual(self.add(type="income", **{"income-category": "salary"}, amount="100").status_code, 302)
        rows = self.query("SELECT type, category, amount FROM transactions ORDER BY id")
        self.assertEqual(rows, [("expense", "grocery", -5.0), ("income", "salary", 100.0)])

    def test_invalid_transactions_are_rejected(self):
        bad = [dict(type="hack"), dict(amount="nan"), dict(amount="inf"), dict(amount="-5"),
               dict(amount="abc"), {"expense-category": "made_up"}, dict(tx_time="25:99"),
               dict(place="x" * 101), dict(comment="x" * 251)]
        for overrides in bad:
            with self.subTest(overrides=overrides):
                self.assertEqual(self.add(**overrides).status_code, 400)
        self.assertEqual(self.query("SELECT COUNT(*) FROM transactions")[0][0], 0)

    def test_update_transaction(self):
        self.add()
        tx_id = self.query("SELECT id FROM transactions")[0][0]
        r = self.client.post("/update_tx", data={
            "tx_id": tx_id, "type": "expense", "expense-category": "dining", "place": "cafe",
            "tx_time": "11:00", "comment": "", "amount": "7.5", "year": YEAR, "month": 3, "day": 4})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.query("SELECT category, amount FROM transactions"), [("dining", -7.5)])

    def test_cannot_touch_other_users_transactions(self):
        self.add()
        tx_id = self.query("SELECT id FROM transactions")[0][0]
        other = self.client.application.test_client()
        self.create_verified_user("other@vsteschenko.me")
        self.login("other@vsteschenko.me", client=other)
        other.post("/delete_tx", data={"tx_id": tx_id, "year": YEAR, "month": 3, "day": 4})
        self.assertEqual(self.query("SELECT COUNT(*) FROM transactions")[0][0], 1)

    def test_bad_query_parameters_do_not_crash(self):
        for url in ["/?year=abc", "/?year=0", "/?month=2&day=31", "/?month=99",
                    "/expenses_by_category?year=x&month=1&day=1", "/report?year=abc",
                    f"/annual_report?year={YEAR}", "/transactions_by_categories_year?category=grocery&year=abc"]:
            with self.subTest(url=url):
                self.assertIn(self.client.get(url).status_code, (200, 400))

    def test_annual_report_survives_unknown_category(self):
        user_id = self.query("SELECT id FROM users")[0][0]
        con = __import__("sqlite3").connect(self.db_path)
        con.execute("INSERT INTO transactions(user_id, amount, timestamp, category, type) VALUES (?,?,?,?,?)",
                    (user_id, -3, f"{YEAR}-01-01 10:00:00", "legacy_cat", "expense"))
        con.commit()
        con.close()
        self.assertEqual(self.client.get(f"/annual_report?year={YEAR}").status_code, 200)
