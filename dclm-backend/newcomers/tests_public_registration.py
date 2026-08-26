from datetime import timedelta
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

    def test_location_is_always_bahrain_even_if_client_tries_to_override(self):
        resp = self.client.post("/api/public/newcomer-registration/", self.valid_payload(location="others"))
        self.assertEqual(resp.status_code, 201)
        newcomer = Newcomer.objects.latest("id")
        self.assertEqual(newcomer.location_id, "bahrain",
            "Location must always be Bahrain for QR registration, regardless of what the client sends.")

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


class PublicMeetingTypesTestCase(APITestCase):
    """
    The public registration form needs the meeting list, but the visitor
    filling it in is not signed in. Found in acceptance testing: the
    "which meeting did you attend" dropdown was simply empty, because the
    form was reading the protected endpoint and getting a 401.
    """
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        MeetingType.objects.create(
            id="fri-worship", name="Friday Worship Service", day="Friday",
            frequency="weekly", detail_level="detailed")
        MeetingType.objects.create(
            id="mon-bs", name="Monday Bible Study", day="Monday",
            frequency="weekly", detail_level="simple")

    def test_anonymous_visitor_can_read_the_meeting_list(self):
        resp = self.client.get("/api/public/meeting-types/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 2)

    def test_the_protected_endpoint_still_refuses_anonymous_access(self):
        """The open endpoint must not weaken the normal one."""
        resp = self.client.get("/api/meeting-types/")
        self.assertIn(resp.status_code, (401, 403))

    def test_it_returns_only_what_the_form_needs(self):
        """Not attendance targets or absence settings, which are none of a
        visitor's business."""
        resp = self.client.get("/api/public/meeting-types/")
        self.assertEqual(set(resp.data[0].keys()), {"id", "name"})

    def test_meetings_come_back_in_a_stable_order(self):
        resp = self.client.get("/api/public/meeting-types/")
        names = [m["name"] for m in resp.data]
        self.assertEqual(names, sorted(names))


class PublicRegistrationErrorMessagesTestCase(APITestCase):
    """
    Which failures stay vague and which name the problem.

    Found in acceptance testing: every rejection produced "We couldn't
    process your submission, please see a leader at the welcome desk."
    That is right for the anti-spam guards, since naming which one
    tripped would help a bot tune around it. It is wrong for an ordinary
    mistake, because the visitor is left with nothing to correct.
    """
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        self.url = "/api/public/newcomer-registration/"

    def _payload(self, **over):
        data = {"name": "Test Visitor", "phone": "+973 3900 0000", "website": "",
                "form_loaded_at": (timezone.now() - timedelta(seconds=30)).isoformat()}
        data.update(over)
        return data

    def test_the_honeypot_stays_vague(self):
        """A bot must not learn which guard caught it."""
        resp = self.client.post(self.url, self._payload(website="http://spam"), format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("detail", resp.data)
        self.assertNotIn("website", resp.data)

    def test_submitting_too_fast_stays_vague(self):
        resp = self.client.post(
            self.url, self._payload(form_loaded_at=timezone.now().isoformat()), format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("detail", resp.data)

    def test_an_ordinary_mistake_names_the_field(self):
        """The visitor has to be able to fix it themselves."""
        resp = self.client.post(self.url, self._payload(name="X" * 200), format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("name", resp.data)
        self.assertNotIn("detail", resp.data)

    def test_a_bad_email_names_the_field(self):
        resp = self.client.post(self.url, self._payload(email="not-an-email"), format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("email", resp.data)

    def test_an_unknown_meeting_names_the_field(self):
        resp = self.client.post(
            self.url, self._payload(meeting_attended="no-such-meeting"), format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("meeting_attended", resp.data)

    def test_a_good_submission_still_succeeds(self):
        resp = self.client.post(self.url, self._payload(), format="json")
        self.assertEqual(resp.status_code, 201)
