from tests.base import AppTestCase, PASSWORD
from tokens import hash_token


class SignupTests(AppTestCase):
    def test_signup_verify_and_login(self):
        r = self.signup("new@vsteschenko.me")
        self.assertEqual(r.status_code, 302)
        self.assertIn("check_email=1", r.headers["Location"])
        token = self.last_token("verification")
        # Opening the link only shows a form (email scanners open links too)
        self.assertEqual(self.client.get(f"/verify?token={token}").status_code, 200)
        self.assertEqual(self.login("new@vsteschenko.me").status_code, 200)  # not verified yet
        self.assertEqual(self.verify().status_code, 200)
        self.assertEqual(self.login("new@vsteschenko.me").status_code, 302)

    def test_login_is_case_insensitive(self):
        self.create_verified_user("Alice@vsteschenko.me")
        self.assertEqual(self.login("ALICE@vsteschenko.me").status_code, 302)

    def test_tokens_are_stored_hashed(self):
        self.signup("hash@vsteschenko.me")
        token = self.last_token("verification")
        stored = self.query("SELECT verification_token FROM users")[0][0]
        self.assertNotEqual(stored, token)
        self.assertEqual(stored, hash_token(token))
        # The stored hash itself must not work as a link
        self.assertEqual(self.client.get(f"/verify?token={stored}").status_code, 404)

    def test_signup_does_not_reveal_existing_accounts(self):
        self.create_verified_user("taken@vsteschenko.me")
        new = self.signup("free@vsteschenko.me", ip="10.0.0.2")
        taken = self.signup("taken@vsteschenko.me", ip="10.0.0.3")
        self.assertEqual(new.status_code, taken.status_code)
        self.assertEqual(new.headers["Location"], taken.headers["Location"])

    def test_attacker_cannot_preregister_someone_elses_email(self):
        # Attacker signs up with the victim's address and their own password
        self.signup("victim@vsteschenko.me", password="attackerpass9", ip="6.6.6.6")
        # Victim later signs up and verifies with their own password
        self.signup("victim@vsteschenko.me", password=PASSWORD, ip="1.2.3.4")
        self.assertEqual(self.verify(PASSWORD).status_code, 200)
        self.assertEqual(self.login("victim@vsteschenko.me", "attackerpass9").status_code, 200)
        self.assertEqual(self.login("victim@vsteschenko.me", PASSWORD).status_code, 302)

    def test_verify_needs_the_signup_password(self):
        self.signup("victim@vsteschenko.me", password=PASSWORD, ip="1.2.3.4")
        # Attacker signs up afterwards; the victim clicks the newest link but
        # the attacker's password is now set, so the victim's password is refused
        self.signup("victim@vsteschenko.me", password="attackerpass9", ip="6.6.6.6")
        self.assertEqual(self.verify(PASSWORD).status_code, 400)
        self.assertEqual(self.query("SELECT is_verified FROM users")[0][0], 0)

    def test_existing_account_gets_a_notice_instead(self):
        self.create_verified_user("taken@vsteschenko.me")
        self.signup("taken@vsteschenko.me", ip="10.0.0.9")
        self.assertEqual(self.count_sent("account_exists"), 1)
        self.assertEqual(self.login("taken@vsteschenko.me").status_code, 302)  # password unchanged

    def test_signup_emails_are_rate_limited_per_ip(self):
        for i in range(10):
            self.signup(f"spam{i}@vsteschenko.me", ip="6.6.6.6")
        self.assertEqual(self.count_sent("verification"), 5)
        # Another client is unaffected
        self.signup("ok@vsteschenko.me", ip="7.7.7.7")
        self.assertEqual(self.count_sent("verification"), 6)


class LoginRateLimitTests(AppTestCase):
    def test_attacker_cannot_lock_out_victim(self):
        self.create_verified_user("victim@vsteschenko.me")
        for i in range(10):
            self.login("victim@vsteschenko.me", "wrong", ip="6.6.6.6")
        self.assertEqual(self.login("victim@vsteschenko.me", ip="1.2.3.4").status_code, 302)

    def test_repeated_failures_block_that_client(self):
        self.create_verified_user("user@vsteschenko.me")
        for _ in range(5):
            self.login("user@vsteschenko.me", "wrong", ip="6.6.6.6")
        r = self.login("user@vsteschenko.me", ip="6.6.6.6")
        self.assertIn(b"Too many login attempts", r.data)

    def test_spoofed_forwarded_for_is_ignored(self):
        self.create_verified_user("user@vsteschenko.me")
        # nginx appends the real address last; earlier values come from the client
        for i in range(5):
            self.login("user@vsteschenko.me", "wrong", ip=f"10.9.9.{i}, 6.6.6.6")
        r = self.login("user@vsteschenko.me", ip="99.99.99.99, 6.6.6.6")
        self.assertIn(b"Too many login attempts", r.data)

    def test_guessing_from_many_ips_is_capped_per_account(self):
        self.create_verified_user("user@vsteschenko.me")
        for i in range(100):
            self.login("user@vsteschenko.me", "wrong", ip=f"8.8.{i // 250}.{i % 250}")
        r = self.login("user@vsteschenko.me", ip="1.2.3.4")
        self.assertIn(b"Too many login attempts", r.data)

    def test_ipv6_addresses_in_one_block_count_as_one_client(self):
        self.create_verified_user("user@vsteschenko.me")
        for i in range(5):
            self.login("user@vsteschenko.me", "wrong", ip=f"2001:db8:1:2::{i + 1}")
        r = self.login("user@vsteschenko.me", ip="2001:db8:1:2::99")
        self.assertIn(b"Too many login attempts", r.data)

    def test_malformed_email_gets_normal_error(self):
        r = self.login("not-an-email", "x")
        self.assertIn(b"Invalid email or password", r.data)


class PasswordTests(AppTestCase):
    def test_reset_flow_and_rate_limit(self):
        self.create_verified_user("u@vsteschenko.me")
        for _ in range(5):
            self.client.post("/forgot_password", data=dict(email="u@vsteschenko.me"))
        self.assertEqual(self.count_sent("reset_password"), 3)
        token = self.last_token("reset_password")
        r = self.client.post("/reset_password",
                             data=dict(token=token, new_password="brandnewpass1", confirm_password="brandnewpass1"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.login("u@vsteschenko.me", "brandnewpass1").status_code, 302)

    def test_reset_requests_do_not_count_as_login_failures(self):
        self.create_verified_user("u@vsteschenko.me")
        for _ in range(10):
            self.client.post("/forgot_password", data=dict(email="nobody@vsteschenko.me"))
        self.assertEqual(self.login("u@vsteschenko.me").status_code, 302)

    def test_password_change_logs_out_other_sessions(self):
        self.create_verified_user("u@vsteschenko.me")
        other = self.client.application.test_client()
        self.login("u@vsteschenko.me")
        self.login("u@vsteschenko.me", client=other)
        self.client.post("/change_password", data=dict(
            current_password=PASSWORD, new_password="changedpass12", confirm_password="changedpass12"))
        self.assertEqual(self.client.get("/").status_code, 200)   # this browser stays in
        self.assertEqual(other.get("/").status_code, 302)         # the other is logged out

    def test_logout_when_logged_out(self):
        self.assertEqual(self.client.get("/logout").status_code, 302)


class DeleteAccountTests(AppTestCase):
    def test_link_only_shows_confirmation(self):
        self.create_verified_user("bye@vsteschenko.me")
        self.login("bye@vsteschenko.me")
        self.client.post("/delete_account", data=dict(email="bye@vsteschenko.me"))
        token = self.last_token("delete_account")

        page = self.client.get(f"/delete_account?token={token}")
        self.assertEqual(page.status_code, 200)
        self.assertTrue(self.query("SELECT 1 FROM users"), "GET must not delete")

        self.client.post("/delete_account", data=dict(token=self.token_in(page.get_data(as_text=True))))
        self.assertFalse(self.query("SELECT 1 FROM users"))

    def test_bad_token(self):
        self.assertEqual(self.client.get("/delete_account?token=nope").status_code, 400)


class StaleSessionTests(AppTestCase):
    def test_stale_session_is_sent_to_login_not_an_error(self):
        self.create_verified_user("u@vsteschenko.me")
        other = self.client.application.test_client()
        self.login("u@vsteschenko.me", client=other)
        self.login("u@vsteschenko.me")
        self.client.post("/change_password", data=dict(
            current_password="goodpassword1", new_password="changedpass12", confirm_password="changedpass12"))
        # The other browser submits a form with its old session
        r = other.post("/", data={"type": "expense", "expense-category": "grocery", "place": "x",
                                  "tx_time": "10:00", "comment": "", "amount": "5"})
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r.headers["Location"])
        self.assertEqual(self.query("SELECT COUNT(*) FROM transactions")[0][0], 0)
