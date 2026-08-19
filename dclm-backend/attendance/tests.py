import datetime

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import AuditLog, Role, RolePermission, User
from core.models import Location
from members.models import Member
from .models import MeetingType, AttendanceSession, AttendanceSessionMember


class AttendanceAPITestCase(APITestCase):
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        self.others = Location.objects.create(id="others", name="Others", note="Qatar")

        self.admin_role = Role.objects.create(name="Administrator")
        RolePermission.objects.create(role=self.admin_role, module="attendance",
            can_view=True, can_create=True, can_edit=True, can_delete=True)
        self.viewer_role = Role.objects.create(name="Viewer")
        RolePermission.objects.create(role=self.viewer_role, module="attendance",
            can_view=True, can_create=False, can_edit=False, can_delete=False)

        self.admin = User.objects.create_user(email="admin@test.com", password="x", role=self.admin_role)
        self.coord = User.objects.create_user(email="coord@test.com", password="x",
            role=self.admin_role, location=self.bahrain)
        self.viewer = User.objects.create_user(email="viewer@test.com", password="x",
            role=self.viewer_role, location=self.bahrain)

        self.detailed_mt = MeetingType.objects.create(
            id="fri-worship", name="Friday Worship Service", day="Friday",
            frequency="weekly", detail_level="detailed", monthly_target=150,
        )
        self.simple_mt = MeetingType.objects.create(
            id="sat-workers", name="Saturday Workers Meeting", day="Saturday",
            frequency="weekly", detail_level="simple",
        )

        self.bahrain_session = AttendanceSession.objects.create(
            meeting_type=self.detailed_mt, date=datetime.date(2026, 8, 14),
            location=self.bahrain, mode="in-person", status="pending",
        )
        self.qatar_session = AttendanceSession.objects.create(
            meeting_type=self.detailed_mt, date=datetime.date(2026, 8, 14),
            location=self.others, mode="online", status="pending",
        )

        self.member1 = Member.objects.create(surname="Uguru", first_name="Chinedu",
            location=self.bahrain, joined_date=datetime.date(2019, 3, 10))
        self.member2 = Member.objects.create(surname="Karim", first_name="Ali",
            location=self.others, joined_date=datetime.date(2023, 4, 19))

    def auth(self, user):
        self.client.force_authenticate(user=user)

    # --- Location scoping ---

    def test_coordinator_only_sees_own_location_sessions(self):
        self.auth(self.coord)
        resp = self.client.get("/api/attendance-sessions/")
        ids = [s["id"] for s in (resp.data["results"] if "results" in resp.data else resp.data)]
        self.assertIn(self.bahrain_session.id, ids)
        self.assertNotIn(self.qatar_session.id, ids)

    # --- Filtering (Batch 3.5 finding: neither meeting_type nor status
    # filtering existed on the backend before the frontend needed them) ---

    def test_filter_by_meeting_type(self):
        AttendanceSession.objects.create(meeting_type=self.simple_mt, date=datetime.date(2026, 8, 15),
            location=self.bahrain, mode="in-person", status="pending")
        self.auth(self.admin)
        resp = self.client.get(f"/api/attendance-sessions/?meeting_type={self.detailed_mt.id}")
        results = resp.data["results"] if "results" in resp.data else resp.data
        self.assertTrue(all(r["meeting_type"] == self.detailed_mt.id for r in results))

    def test_filter_by_status(self):
        self.auth(self.admin)
        resp = self.client.get("/api/attendance-sessions/?status=pending")
        results = resp.data["results"] if "results" in resp.data else resp.data
        self.assertTrue(all(r["status"] == "pending" for r in results))

    def test_ordering_by_total_reflects_real_headcount_sum(self):
        """
        total is a Python property, not a DB field , this confirms the
        DB-level annotation actually sorts correctly, not just that the
        query doesn't error.
        """
        low = AttendanceSession.objects.create(meeting_type=self.detailed_mt, date=datetime.date(2026, 8, 1),
            location=self.bahrain, mode="in-person", status="filled", men=5, women=5)
        high = AttendanceSession.objects.create(meeting_type=self.detailed_mt, date=datetime.date(2026, 8, 8),
            location=self.bahrain, mode="in-person", status="filled", men=50, women=50)
        self.auth(self.admin)
        resp = self.client.get("/api/attendance-sessions/?ordering=-total_computed")
        results = resp.data["results"] if "results" in resp.data else resp.data
        ids_in_order = [r["id"] for r in results if r["id"] in (low.id, high.id)]
        self.assertEqual(ids_in_order, [high.id, low.id], "Highest total must sort first with -total_computed.")

    # --- Stats endpoint ---

    def test_stats_counts_are_correct_and_location_scoped(self):
        self.auth(self.coord)
        resp = self.client.get("/api/attendance-sessions/stats/")
        self.assertEqual(resp.data["pending"], 1)  # only bahrain_session, per setUp
        self.assertEqual(resp.data["filled"], 0)

    def test_stats_sessions_this_month_uses_real_calendar_month_not_string_matching(self):
        """
        Specifically guards against the date__startswith risk , a date
        from a different year but the same day-of-month digits must not
        accidentally match.
        """
        from django.utils import timezone
        today = timezone.localdate()
        AttendanceSession.objects.create(meeting_type=self.detailed_mt, date=today,
            location=self.bahrain, mode="in-person", status="pending")
        wrong_year_same_day = today.replace(year=today.year - 5)
        AttendanceSession.objects.create(meeting_type=self.detailed_mt, date=wrong_year_same_day,
            location=self.bahrain, mode="in-person", status="pending")
        self.auth(self.admin)
        resp = self.client.get("/api/attendance-sessions/stats/")
        # Only the genuinely-this-month session should count, regardless
        # of how many previous years happen to share the same day number.
        sessions_this_month_qs_count = AttendanceSession.objects.filter(
            date__year=today.year, date__month=today.month
        ).count()
        self.assertEqual(resp.data["sessions_this_month"], sessions_this_month_qs_count)

    # --- record action: headcounts, status flip, atomicity ---

    def test_record_sets_headcounts_and_flips_status_to_filled(self):
        self.auth(self.admin)
        resp = self.client.post(f"/api/attendance-sessions/{self.bahrain_session.id}/record/", {
            "men": 38, "women": 52, "youth_boys": 14, "youth_girls": 16,
            "children_boys": 11, "children_girls": 11,
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.bahrain_session.refresh_from_db()
        self.assertEqual(self.bahrain_session.status, "filled")
        self.assertEqual(self.bahrain_session.total, 142)

    def test_status_is_read_only_on_plain_patch(self):
        self.auth(self.admin)
        resp = self.client.patch(f"/api/attendance-sessions/{self.bahrain_session.id}/", {"status": "filled"})
        self.bahrain_session.refresh_from_db()
        self.assertEqual(self.bahrain_session.status, "pending",
            "status must only change via record(), never a plain PATCH.")

    def test_simple_meeting_rejects_youth_and_children_counts(self):
        simple_session = AttendanceSession.objects.create(
            meeting_type=self.simple_mt, date=datetime.date(2026, 8, 15),
            location=self.bahrain, mode="in-person", status="pending",
        )
        self.auth(self.admin)
        resp = self.client.post(f"/api/attendance-sessions/{simple_session.id}/record/", {
            "men": 12, "women": 14, "youth_boys": 3,
        })
        self.assertEqual(resp.status_code, 400)
        simple_session.refresh_from_db()
        self.assertEqual(simple_session.status, "pending", "Rejected record must not partially apply.")

    # --- Named attendance: no location restriction ---

    def test_named_attendance_allows_any_location_member(self):
        self.auth(self.admin)
        resp = self.client.post(f"/api/attendance-sessions/{self.bahrain_session.id}/record/", {
            "men": 1, "women": 0, "track_named": True,
            "attendee_ids": [self.member1.id, self.member2.id],  # Bahrain session, but member2 is Qatar
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK,
            "Named attendance must allow any member regardless of location (Batch 0.2 decision).")
        recorded = set(AttendanceSessionMember.objects.filter(session=self.bahrain_session).values_list("member_id", flat=True))
        self.assertEqual(recorded, {self.member1.id, self.member2.id})

    def test_unknown_member_id_in_attendee_ids_rejected(self):
        self.auth(self.admin)
        resp = self.client.post(f"/api/attendance-sessions/{self.bahrain_session.id}/record/", {
            "men": 1, "track_named": True, "attendee_ids": [999999],
        })
        self.assertEqual(resp.status_code, 400)

    # --- Audit logging dedup ---

    def test_record_produces_exactly_one_audit_entry(self):
        self.auth(self.admin)
        AuditLog.objects.all().delete()
        self.client.post(f"/api/attendance-sessions/{self.bahrain_session.id}/record/", {"men": 5, "women": 5})
        entries = AuditLog.objects.filter(entity_type="Attendance Session", entity_name__icontains="Friday Worship")
        self.assertEqual(entries.count(), 1, f"Expected exactly 1 entry, got {entries.count()}")
        self.assertEqual(entries.first().action, "Recorded attendance")


class RecurringSessionGenerationTestCase(TestCase):
    """
    Direct tests of the management command that fulfills the Batch 0.2
    approved decision , this logic was never actually built before now.
    """
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        self.others = Location.objects.create(id="others", name="Others", note="Qatar")
        self.weekly_mt = MeetingType.objects.create(
            id="fri-worship", name="Friday Worship Service", day="Friday",
            frequency="weekly", detail_level="detailed", monthly_target=150,
        )
        self.occasional_mt = MeetingType.objects.create(
            id="gck", name="Global Crusade with Kumuyi", day=",",
            frequency="occasional", detail_level="detailed",
        )

    def test_creates_one_session_per_location_for_weekly_meeting(self):
        call_command("generate_recurring_sessions")
        sessions = AttendanceSession.objects.filter(meeting_type=self.weekly_mt)
        self.assertEqual(sessions.count(), 2, "Expected one session per location (Bahrain + Others).")
        self.assertTrue(sessions.filter(location=self.bahrain).exists())
        self.assertTrue(sessions.filter(location=self.others).exists())

    def test_does_not_create_sessions_for_occasional_meetings(self):
        call_command("generate_recurring_sessions")
        self.assertFalse(
            AttendanceSession.objects.filter(meeting_type=self.occasional_mt).exists(),
            "Occasional meetings must never be auto-generated.",
        )

    def test_idempotent_running_twice_does_not_duplicate(self):
        call_command("generate_recurring_sessions")
        first_count = AttendanceSession.objects.filter(meeting_type=self.weekly_mt).count()
        call_command("generate_recurring_sessions")
        second_count = AttendanceSession.objects.filter(meeting_type=self.weekly_mt).count()
        self.assertEqual(first_count, second_count, "Running the command twice must not create duplicates.")

    def test_generated_date_is_actually_the_correct_weekday(self):
        call_command("generate_recurring_sessions")
        session = AttendanceSession.objects.filter(meeting_type=self.weekly_mt, location=self.bahrain).first()
        self.assertIsNotNone(session)
        self.assertEqual(session.date.strftime("%A"), "Friday",
            f"Generated date {session.date} is not actually a Friday.")

    def test_generated_date_is_today_or_in_the_future(self):
        call_command("generate_recurring_sessions")
        session = AttendanceSession.objects.filter(meeting_type=self.weekly_mt, location=self.bahrain).first()
        self.assertGreaterEqual(session.date, timezone.localdate())

    def test_unrecognized_day_value_is_skipped_not_crashed(self):
        MeetingType.objects.create(
            id="broken", name="Broken Meeting", day="Someday",  # not a real weekday
            frequency="weekly", detail_level="simple",
        )
        # Should not raise , just skip with a warning
        call_command("generate_recurring_sessions")
        self.assertFalse(AttendanceSession.objects.filter(meeting_type_id="broken").exists())

    def test_no_locations_does_not_crash(self):
        Location.objects.all().delete()
        call_command("generate_recurring_sessions")  # should not raise


class LiveCheckInTestCase(APITestCase):
    """
    The real-time, single-tap check-in endpoint , deliberately separate
    from record()'s batch submission, so concurrent ushers at different
    doors can't overwrite each other's taps.
    """
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        self.role = Role.objects.create(name="Administrator")
        RolePermission.objects.create(role=self.role, module="attendance",
            can_view=True, can_create=True, can_edit=True, can_delete=True)
        self.admin = User.objects.create_user(email="admin@test.com", password="x", role=self.role)
        self.mt = MeetingType.objects.create(id="fri-worship", name="Friday Worship Service",
            day="Friday", frequency="weekly", detail_level="detailed", monthly_target=150, counts_for_absence=True)
        self.session = AttendanceSession.objects.create(meeting_type=self.mt, date=datetime.date(2026, 8, 14),
            location=self.bahrain, mode="in-person", status="pending")
        self.member = Member.objects.create(surname="Noor", first_name="Fatima", location=self.bahrain,
            joined_date=datetime.date(2024, 1, 1))

    def auth(self):
        self.client.force_authenticate(user=self.admin)

    def test_check_in_creates_attendance_record(self):
        self.auth()
        resp = self.client.post(f"/api/attendance-sessions/{self.session.id}/check_in/", {
            "member_id": self.member.id, "mode": "in-person",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(AttendanceSessionMember.objects.filter(session=self.session, member=self.member).exists())

    def test_check_in_does_not_touch_headcounts_or_status(self):
        """Headcounts stay the source of truth (Batch 0.2) , a real-time
        check-in must not silently fill them in or flip session status."""
        self.auth()
        self.client.post(f"/api/attendance-sessions/{self.session.id}/check_in/", {"member_id": self.member.id})
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, "pending")
        self.assertEqual(self.session.men, 0)

    def test_check_out_removes_attendance_record(self):
        AttendanceSessionMember.objects.create(session=self.session, member=self.member)
        self.auth()
        resp = self.client.delete(f"/api/attendance-sessions/{self.session.id}/check_in/", {
            "member_id": self.member.id,
        }, content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(AttendanceSessionMember.objects.filter(session=self.session, member=self.member).exists())

    def test_patch_changes_mode_without_affecting_presence(self):
        AttendanceSessionMember.objects.create(session=self.session, member=self.member, mode="in-person")
        self.auth()
        resp = self.client.patch(f"/api/attendance-sessions/{self.session.id}/check_in/", {
            "member_id": self.member.id, "mode": "online",
        }, content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        record = AttendanceSessionMember.objects.get(session=self.session, member=self.member)
        self.assertEqual(record.mode, "online")

    def test_patch_on_not_checked_in_member_returns_404(self):
        self.auth()
        resp = self.client.patch(f"/api/attendance-sessions/{self.session.id}/check_in/", {
            "member_id": self.member.id, "mode": "online",
        }, content_type="application/json")
        self.assertEqual(resp.status_code, 404)

    def test_repeated_check_in_updates_rather_than_duplicates(self):
        """Tapping check-in twice with different modes must update the
        one record, not create a second (unique_together enforces this,
        but confirm the endpoint uses update_or_create correctly)."""
        self.auth()
        self.client.post(f"/api/attendance-sessions/{self.session.id}/check_in/", {
            "member_id": self.member.id, "mode": "in-person",
        })
        self.client.post(f"/api/attendance-sessions/{self.session.id}/check_in/", {
            "member_id": self.member.id, "mode": "online",
        })
        records = AttendanceSessionMember.objects.filter(session=self.session, member=self.member)
        self.assertEqual(records.count(), 1)
        self.assertEqual(records.first().mode, "online")

    def test_check_in_response_body_reflects_the_change_immediately(self):
        """
        Regression test for a real bug caught via end-to-end API testing,
        not the unit tests above: those checked the database directly
        and passed, while the actual HTTP response body was silently
        stale , session.attendees.all() was returning a prefetch cache
        populated before this request's own create, not the fresh state.
        """
        self.auth()
        resp = self.client.post(f"/api/attendance-sessions/{self.session.id}/check_in/", {
            "member_id": self.member.id, "mode": "in-person",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["attendees"]), 1,
            "The response body itself must reflect the just-created check-in, not a stale prefetch cache.")
        self.assertEqual(resp.data["attendees"][0]["member"], self.member.id)

    def test_check_in_without_member_id_returns_400(self):
        self.auth()
        resp = self.client.post(f"/api/attendance-sessions/{self.session.id}/check_in/", {})
        self.assertEqual(resp.status_code, 400)

    def test_no_location_restriction_on_check_in(self):
        """Batch 0.2 decision: any member, any location, can be checked
        into any session , same rule the older named-attendance flow follows."""
        other_location = Location.objects.create(id="others", name="Others", note="Qatar")
        other_member = Member.objects.create(surname="Karim", first_name="Ali", location=other_location,
            joined_date=datetime.date(2023, 1, 1))
        self.auth()
        resp = self.client.post(f"/api/attendance-sessions/{self.session.id}/check_in/", {
            "member_id": other_member.id,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(AttendanceSessionMember.objects.filter(session=self.session, member=other_member).exists())
