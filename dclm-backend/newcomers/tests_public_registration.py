"""
Tests for the public QR self-registration endpoint (Batch 3.6). A real
unauthenticated write endpoint is a genuine attack surface, so this
gets the same level of scrutiny as login's security tests.
"""
import datetime

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from attendance.models import MeetingType
from core.models import Location
from members.models import Member
from .models import Newcomer, NewcomerTask, NewcomerSource, PublicRegistrationAttempt


class PublicRegistrationTestCase(APITestCase):
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        self.others = Location.objects.create(id="others", name="Others", note="Qatar")
        self.mt = MeetingType.objects.create(id="fri-worship", name="Friday Worship Service",
            day="Friday", frequency="weekly", detail_level="detailed", monthly_target=150)

    def valid_payload(self, **overrides):
        payload = {
            "name": "Fatima Al-Sayed",
            "address": "Flat 12, Building 45", "city_governorate": "Manama",
            "phone": "+973 3600 1234", "email": "fatima@example.com",
            "gender": "Female", "age_group": "20_and_above",
            "prayer_request": "Peace for my family", "meeting_attended": self.mt.id,
            "is_first_timer": True, "is_new_resident": False,
            "form_loaded_at": (timezone.now() - datetime.timedelta(seconds=5)).isoformat(),
        }
        payload.update(overrides)
        return payload

    # --- No authentication required at all , the most basic, essential check ---

    def test_works_without_any_authentication(self):
        resp = self.client.post("/api/public/newcomer-registration/", self.valid_payload())
        self.assertEqual(resp.status_code, 201)

    # --- Auto-set fields, not client-controlled ---

    def test_location_follows_the_qr_code_but_only_to_an_existing_location(self):
        """Version 11: each location has its own QR code, so a visitor lands
        in the pipeline of the location they attended. Version 10 always
        used the main location. Anything unknown still goes there."""
        resp = self.client.post("/api/public/newcomer-registration/", self.valid_payload(location="others"))
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(Newcomer.objects.latest("id").location_id, "others")
        resp = self.client.post("/api/public/newcomer-registration/", self.valid_payload(location="made-up"))
        self.assertEqual(Newcomer.objects.latest("id").location_id, "bahrain")

    def test_source_is_auto_tagged_as_qr_self_registration(self):
        self.client.post("/api/public/newcomer-registration/", self.valid_payload())
        newcomer = Newcomer.objects.latest("id")
        self.assertEqual(newcomer.source.name, "Church website (QR self-registration)")

    def test_stage_is_new_and_unassigned(self):
        self.client.post("/api/public/newcomer-registration/", self.valid_payload())
        newcomer = Newcomer.objects.latest("id")
        self.assertEqual(newcomer.stage, "new")
        self.assertIsNone(newcomer.assigned_to)

    def test_response_does_not_leak_internal_id_or_details(self):
        resp = self.client.post("/api/public/newcomer-registration/", self.valid_payload())
        self.assertNotIn("id", resp.data)
        self.assertEqual(set(resp.data.keys()), {"detail"})

    # --- Real intake fields actually persist ---

    def test_all_fields_saved_correctly(self):
        self.client.post("/api/public/newcomer-registration/", self.valid_payload())
        newcomer = Newcomer.objects.latest("id")
        self.assertEqual(newcomer.address, "Flat 12, Building 45")
        self.assertEqual(newcomer.city_governorate, "Manama")
        self.assertEqual(newcomer.gender, "Female")
        self.assertTrue(newcomer.is_first_timer)
        self.assertEqual(newcomer.meeting_attended_id, "fri-worship")

    # --- Shared logic actually reused, not reimplemented separately ---

    def test_auto_tasks_created_same_as_authenticated_path(self):
        self.client.post("/api/public/newcomer-registration/", self.valid_payload(wants_visit=True, wants_salvation_info=True))
        newcomer = Newcomer.objects.latest("id")
        tasks = list(NewcomerTask.objects.filter(newcomer=newcomer).values_list("text", flat=True))
        self.assertIn("Schedule a home visit", tasks)
        self.assertIn("Have a salvation conversation", tasks)

    def test_invited_by_matching_works_same_as_authenticated_path(self):
        m = Member.objects.create(surname="Thomas", first_name="Grace", location=self.bahrain,
            joined_date=datetime.date.today())
        self.client.post("/api/public/newcomer-registration/", self.valid_payload(invited_by_name="Grace Thomas"))
        newcomer = Newcomer.objects.latest("id")
        self.assertEqual(newcomer.invited_by_member_id, m.id)

    # --- Security: honeypot ---

    def test_honeypot_rejects_with_generic_message(self):
        resp = self.client.post("/api/public/newcomer-registration/", self.valid_payload(website="http://spam.example"))
        self.assertEqual(resp.status_code, 400)
        self.assertIn("welcome desk", resp.data["detail"])
        self.assertFalse(Newcomer.objects.exists())
        attempt = PublicRegistrationAttempt.objects.latest("id")
        self.assertEqual(attempt.reason, "honeypot")
        self.assertFalse(attempt.successful)

    # --- Security: too-fast submission ---

    def test_too_fast_submission_rejected(self):
        resp = self.client.post("/api/public/newcomer-registration/", self.valid_payload(
            form_loaded_at=timezone.now().isoformat(),  # submitted "now" , zero elapsed time
        ))
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(Newcomer.objects.exists())
        attempt = PublicRegistrationAttempt.objects.latest("id")
        self.assertEqual(attempt.reason, "too_fast")

    def test_realistic_timing_succeeds(self):
        resp = self.client.post("/api/public/newcomer-registration/", self.valid_payload())
        self.assertEqual(resp.status_code, 201)

    # --- Security: rate limiting ---

    def test_rate_limit_allows_up_to_five_then_blocks(self):
        for i in range(5):
            resp = self.client.post("/api/public/newcomer-registration/", self.valid_payload(name=f"Person {i}"))
            self.assertEqual(resp.status_code, 201, f"Submission {i+1} should succeed")
        resp = self.client.post("/api/public/newcomer-registration/", self.valid_payload(name="Person 6"))
        self.assertEqual(resp.status_code, 429)
        self.assertEqual(Newcomer.objects.count(), 5, "The 6th (blocked) attempt must not create a record.")

    # --- Validation errors are correctly distinguished from security rejections ---

    def test_missing_required_name_returns_real_validation_error_not_mislabeled_as_honeypot(self):
        """
        Regression test for a real bug caught and fixed while building
        this: a garbled branch would have logged every ordinary
        validation failure as a HONEYPOT hit, corrupting the security
        log's accuracy. This confirms the fix holds.
        """
        payload = self.valid_payload()
        del payload["name"]
        resp = self.client.post("/api/public/newcomer-registration/", payload)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("name", resp.data)  # real field-level feedback, not the generic message
        attempt = PublicRegistrationAttempt.objects.latest("id")
        self.assertEqual(attempt.reason, "invalid_data",
            "A genuine validation failure must be logged as invalid_data, not mislabeled as honeypot.")

    # --- Every attempt is logged, success or failure ---

    def test_successful_attempt_is_logged(self):
        self.client.post("/api/public/newcomer-registration/", self.valid_payload())
        attempt = PublicRegistrationAttempt.objects.latest("id")
        self.assertTrue(attempt.successful)
        self.assertEqual(attempt.reason, "success")


class RegistrationPerPhoneTests(APITestCase):
    """P10 (review, 25 October 2026): visitors on the church Wi-Fi share one
    address, so each phone is counted by itself."""

    def setUp(self):
        from core.models import Location
        self.bh = Location.objects.get_or_create(id="bahrain", defaults={"name": "Bahrain HQ", "is_core": True})[0]
        from newcomers.models import NewcomerSource
        self.src = NewcomerSource.objects.get_or_create(name="QR code")[0]

    def post(self, name, device):
        import datetime as dt
        loaded = (timezone.now() - dt.timedelta(seconds=30)).isoformat()
        return self.client.post("/api/public/newcomer-registration/", {
            "name": name, "phone": "", "email": "", "source": self.src.id, "form_loaded_at": loaded,
            "device_id": device, "website": ""}, format="json", REMOTE_ADDR="10.0.0.1")

    def test_many_phones_on_one_wifi_all_get_in(self):
        for i in range(12):
            r = self.post(f"Visitor {i}", f"phone-{i}")
            self.assertEqual(r.status_code, 201, (i, r.data))

    def test_one_phone_is_limited_and_an_administrator_can_lift_it(self):
        from accounts.models import Role, RolePermission, User
        for i in range(5):
            self.assertEqual(self.post(f"Family {i}", "phone-a").status_code, 201)
        self.assertEqual(self.post("Family 6", "phone-a").status_code, 429)
        role = Role.objects.get_or_create(name="Administrator")[0]
        for m in ("newcomers", "admin"):
            RolePermission.objects.update_or_create(role=role, module=m, defaults=dict(can_view=True, can_edit=True))
        admin = User.objects.create_user(email="adm@t.com", password="x", role=role)
        self.client.force_authenticate(admin)
        rows = self.client.get("/api/newcomers-registration-blocks/").data["results"]
        self.assertEqual((rows[0]["device_id"], rows[0]["still_blocked"]), ("phone-a", True))
        self.client.post("/api/newcomers-registration-blocks/", {"device_id": "phone-a"}, format="json")
        self.client.force_authenticate(None)
        self.assertEqual(self.post("Family 6", "phone-a").status_code, 201)


class BulkAssignNewcomersTests(APITestCase):
    """Item 13: several newcomers given one shepherd, same rules as one at a time."""

    def test_assign_and_gender_rule(self):
        from accounts.models import Role, RolePermission, User
        bh = Location.objects.get_or_create(id="bahrain", defaults={"name": "Bahrain HQ", "is_core": True})[0]
        src = NewcomerSource.objects.get_or_create(name="Walk-in")[0]
        role = Role.objects.get_or_create(name="Follow-up")[0]
        RolePermission.objects.update_or_create(role=role, module="newcomers", defaults=dict(can_view=True, can_edit=True))
        me = User.objects.create_user(email="me@t.com", password="x", role=role)
        henry = User.objects.create_user(email="h@t.com", password="x", can_shepherd=True, gender="Male", location=bh)
        a = Newcomer.objects.create(name="Kofi A", source=src, location=bh, gender="Male", created_at=timezone.now(), stage_since=timezone.localdate())
        b = Newcomer.objects.create(name="Ama B", source=src, location=bh, gender="Female", created_at=timezone.now(), stage_since=timezone.localdate())
        self.client.force_authenticate(me)
        r = self.client.post("/api/newcomers-bulk-assign/", {"newcomer_ids": [a.id, b.id], "shepherd_id": henry.id}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("Ama B (a woman)", r.data["detail"])
        r = self.client.post("/api/newcomers-bulk-assign/", {"newcomer_ids": [a.id], "shepherd_id": henry.id}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        a.refresh_from_db()
        self.assertEqual(a.assigned_to, henry)
