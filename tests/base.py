import os
import re
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import tests.conftest  # noqa: F401  (sets env vars before the app is imported)
from app import app

PASSWORD = "goodpassword1"


class AppTestCase(unittest.TestCase):
    """Fresh database and test client for every test. Emails are captured, not sent."""

    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        app.config.update(DATABASE=self.db_path, TESTING=True, WTF_CSRF_ENABLED=False)
        self.client = app.test_client()
        self.sent = []  # (kind, email, token)
        self._patches = [
            patch(f"CRUD.user.send_{kind}_email",
                  side_effect=lambda email, token, kind=kind: self.sent.append((kind, email, token)))
            for kind in ("verification", "reset_password", "delete_account")
        ] + [patch("CRUD.user.send_account_exists_email",
                   side_effect=lambda email: self.sent.append(("account_exists", email, None)))]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        os.unlink(self.db_path)

    # helpers
    def query(self, sql, *args):
        con = sqlite3.connect(self.db_path)
        try:
            return con.execute(sql, args).fetchall()
        finally:
            con.close()

    def signup(self, email, password=PASSWORD, client=None, ip="10.0.0.1"):
        return (client or self.client).post(
            "/signup", data=dict(email=email, password=password, confirm_password=password),
            headers={"X-Forwarded-For": ip})

    def verify(self, password=PASSWORD, token=None):
        token = token or self.last_token("verification")
        return self.client.post("/verify", data=dict(token=token, password=password))

    def create_verified_user(self, email, password=PASSWORD):
        self.signup(email, password)
        self.verify(password)

    def login(self, email, password=PASSWORD, ip="10.0.0.1", client=None):
        return (client or self.client).post(
            "/login", data=dict(email=email, password=password), headers={"X-Forwarded-For": ip})

    def last_token(self, kind):
        return [t for k, _, t in self.sent if k == kind][-1]

    def count_sent(self, kind):
        return sum(1 for k, _, _ in self.sent if k == kind)

    @staticmethod
    def token_in(html):
        return re.search(r'name="token" value="([^"]+)"', html).group(1)
