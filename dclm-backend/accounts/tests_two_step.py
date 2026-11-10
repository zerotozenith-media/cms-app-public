"""Two-step sign-in (approved 10 November 2026)."""
import time
from unittest import mock

from rest_framework.test import APITestCase

from accounts import two_step as ts
from accounts.models import AuditLog, Role, RolePermission, User
from core import settings_store


def now_number(user_or_secret, ahead=0):
    secret = user_or_secret if isinstance(user_or_secret, str) else ts.unseal(user_or_secret.two_step_secret)
    return ts.number(secret, int(time.time() // ts.STEP) + ahead)


class Base(APITestCase):
    def setUp(self):
        mk = lambda n, t: Role.objects.update_or_create(name=n, defaults={"two_step": t})[0]  # noqa: E731
        self.admin_role = mk("Administrator", "required")
        RolePermission.objects.update_or_create(role=self.admin_role, module="admin", defaults=dict(can_view=True, can_create=True, can_edit=True, can_delete=True))
        self.acc_role = mk("Accounts", "choose")
        self.off_role = mk("Follow-up", "off")
        self.admin = User.objects.create_user(email="a@t.com", password="Pass12345!", role=self.admin_role)
        self.admin2 = User.objects.create_user(email="b@t.com", password="Pass12345!", role=self.admin_role)
        self.acc = User.objects.create_user(email="c@t.com", password="Pass12345!", role=self.acc_role)
        self.shep = User.objects.create_user(email="d@t.com", password="Pass12345!", role=self.off_role)

    def login(self, email, **extra):
        return self.client.post("/api/auth/login/", {"email": email, "password": "Pass12345!", **extra}, format="json")

    def step(self, ticket, code, **extra):
        return self.client.post("/api/auth/two-step/", {"ticket": ticket, "code": code, **extra}, format="json")

    def set_up(self, user):
        r = self.login(user.email)
        secret = r.data["secret"].replace(" ", "")
        r2 = self.step(r.data["ticket"], ts.number(secret, int(time.time() // ts.STEP)))
        self.assertEqual(r2.status_code, 200, r2.data)
        user.refresh_from_db()
        return r2


class SignInTests(Base):
    def test_a_role_with_two_step_off_signs_straight_in(self):
        r = self.login("d@t.com")
        self.assertIn("access", r.data)
        r = self.login("c@t.com")                    # Person chooses, not turned on
        self.assertIn("access", r.data)

    def test_a_required_role_sets_it_up_at_sign_in(self):
        r = self.login("a@t.com")
        self.assertEqual(r.data["two_step"], "setup")
        self.assertNotIn("access", r.data)
        self.assertTrue(r.data["otpauth"].startswith("otpauth://totp/DCLM%20Bahrain"))
        bad = self.step(r.data["ticket"], "000000")
        self.assertEqual(bad.status_code, 400)
        self.assertIn("not right", bad.data["detail"])
        ok = self.set_up(self.admin)
        self.assertIn("access", ok.data)
        self.assertEqual(len(ok.data["backup_codes"]), 10)
        self.assertTrue(self.admin.two_step_secret)
        self.assertNotIn(ok.data["backup_codes"][0].replace("-", ""), str(self.admin.two_step_backup))
        self.assertTrue(AuditLog.objects.filter(action="Turned on", entity_type="Two-step sign-in").exists())

    def test_then_every_sign_in_asks_for_the_number_once(self):
        self.set_up(self.admin)
        r = self.login("a@t.com")
        self.assertEqual(r.data["two_step"], "code")
        n = now_number(self.admin, 1)
        ok = self.step(r.data["ticket"], n)
        self.assertIn("access", ok.data)
        again = self.step(self.login("a@t.com").data["ticket"], n)      # the same number twice
        self.assertEqual(again.status_code, 400)

    def test_a_backup_code_works_once(self):
        codes = self.set_up(self.admin).data["backup_codes"]
        ok = self.step(self.login("a@t.com").data["ticket"], codes[0].lower())
        self.assertIn("access", ok.data)
        self.assertEqual(ok.data["backup_left"], 9)
        self.assertEqual(self.step(self.login("a@t.com").data["ticket"], codes[0]).status_code, 400)

    def test_a_remembered_browser_is_not_asked_until_reset(self):
        self.set_up(self.admin)
        device = self.step(self.login("a@t.com").data["ticket"], now_number(self.admin, 1), remember=True).data["device"]
        self.assertIn("access", self.login("a@t.com", device=device).data)
        settings_store.set_value("two_step_remember_days", 0)
        self.assertEqual(self.login("a@t.com", device=device).data["two_step"], "code")
        settings_store.set_value("two_step_remember_days", 30)
        self.client.force_authenticate(self.admin2)
        r = self.client.post(f"/api/users/{self.admin.id}/reset-two-step/")
        self.assertEqual(r.status_code, 200, r.data)
        self.client.force_authenticate(None)
        self.assertEqual(self.login("a@t.com", device=device).data["two_step"], "setup")

    def test_wrong_numbers_lock_sign_in_like_wrong_passwords(self):
        t = self.login("a@t.com").data["ticket"]
        for _ in range(5):
            self.step(t, "123456")
        r = self.step(t, "123456")
        self.assertEqual(r.status_code, 429)

    def test_an_old_or_forged_ticket_is_refused(self):
        r = self.step("nonsense", "123456")
        self.assertTrue(r.data["expired"])
        with mock.patch("accounts.two_step.TICKET_MINUTES", -1):
            r = self.step(self.login("a@t.com").data["ticket"], "123456")
        self.assertEqual(r.status_code, 400)

    def test_a_password_reset_does_not_skip_the_second_step(self):
        from accounts.views import second_step
        self.assertEqual(second_step(self.admin)["two_step"], "setup")
        self.assertIsNone(second_step(self.shep))


class ProfileTests(Base):
    def test_a_person_who_chooses_turns_it_on_and_off(self):
        self.client.force_authenticate(self.acc)
        self.assertEqual(self.client.get("/api/auth/me/two-step/").data, {"mode": "choose", "on": False, "on_since": None, "backup_left": 0})
        s = self.client.post("/api/auth/me/two-step/", {"action": "start"}, format="json").data
        secret = s["secret"].replace(" ", "")
        r = self.client.post("/api/auth/me/two-step/", {"action": "confirm", "ticket": s["ticket"], "code": now_number(secret)}, format="json")
        self.assertEqual(len(r.data["backup_codes"]), 10)
        self.acc.refresh_from_db()
        r = self.client.post("/api/auth/me/two-step/", {"action": "new_codes", "code": now_number(self.acc, 1)}, format="json")
        self.assertEqual(len(r.data["backup_codes"]), 10)
        r = self.client.post("/api/auth/me/two-step/", {"action": "off", "code": r.data["backup_codes"][0]}, format="json")
        self.assertEqual(r.data, {"on": False})

    def test_required_cannot_be_turned_off_and_off_is_not_offered(self):
        self.set_up(self.admin)
        self.client.force_authenticate(self.admin)
        r = self.client.post("/api/auth/me/two-step/", {"action": "off", "code": now_number(self.admin, 1)}, format="json")
        self.assertIn("cannot be turned off", r.data["detail"])
        self.client.force_authenticate(self.shep)
        r = self.client.post("/api/auth/me/two-step/", {"action": "start"}, format="json")
        self.assertIn("not offered", r.data["detail"])

    def test_an_administrator_cannot_reset_their_own(self):
        self.set_up(self.admin)
        self.client.force_authenticate(self.admin)
        r = self.client.post(f"/api/users/{self.admin.id}/reset-two-step/")
        self.assertEqual(r.status_code, 400)
        self.assertIn("another Administrator", r.data["fix"])


class StartsOffTests(APITestCase):
    """Two-step sign-in starts Off for every role (10 November 2026)."""

    def test_no_role_needs_two_step_after_migrating(self):

        self.assertFalse(Role.objects.exclude(two_step="off").exists())
