"""
Tests for the check_absences management command , the automatic,
no-button-needed absence-detection mechanism at the heart of the real
member follow-up feature. Given real consequences (creating real tasks
assigned to real shepherds), this gets the same scrutiny as the
security-sensitive tests elsewhere in this project.
"""
import datetime

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from core.models import Location
from accounts.models import User, Role, RolePermission
from members.models import Member, MemberFollowUpTask
from .models import MeetingType, AttendanceSession, AttendanceSessionMember


class CheckAbsencesCommandTestCase(TestCase):
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        self.role = Role.objects.create(name="Location Coordinator")
        self.shepherd = User.objects.create_user(email="shepherd@test.com", password="x", role=self.role,
            first_name="Grace", last_name="Thomas")

        self.now = timezone.now()
        # start_time is meant to be interpreted as local (Bahrain)
        # wall-clock time when the command combines it with a session
        # date , matching how an admin would naturally enter "starts at
        # 6pm". Constructing test values here must convert through
        # timezone.localtime() first, not read .time() off a UTC-aware
        # datetime directly , that would extract UTC wall-clock time,
        # which the command's own make_aware() would then misinterpret
        # as local time, shifting everything by the UTC+3 offset. Found
        # this exact mistake empirically when a "1 hour ago" test value
        # was actually being treated as several hours further past.
        past_start = timezone.localtime(self.now - datetime.timedelta(hours=5)).time().replace(microsecond=0)
        self.tracked_mt = MeetingType.objects.create(
            id="fri-worship", name="Friday Worship Service", day="Friday",
            frequency="weekly", detail_level="detailed", counts_for_absence=True,
            start_time=past_start,
        )
        self.untracked_mt = MeetingType.objects.create(
            id="mon-bs", name="Monday Bible Study", day="Monday",
            frequency="weekly", detail_level="detailed", counts_for_absence=False,
            start_time=past_start,
        )
        self.no_start_time_mt = MeetingType.objects.create(
            id="sat-workers", name="Saturday Workers Meeting", day="Saturday",
            frequency="weekly", detail_level="simple", counts_for_absence=True,
            start_time=None,
        )

        self.member_present = Member.objects.create(surname="Uguru", first_name="Chinedu",
            location=self.bahrain, joined_date=datetime.date(2019, 1, 1), assigned_to=self.shepherd)
        self.member_absent = Member.objects.create(surname="Noor", first_name="Fatima",
            location=self.bahrain, joined_date=datetime.date(2024, 1, 1), assigned_to=self.shepherd)

    def _session(self, meeting_type, date=None):
        return AttendanceSession.objects.create(
            meeting_type=meeting_type, date=date or self.now.date(),
            location=self.bahrain, mode="in-person", status="pending",
        )

    # --- Core behavior ---

    def test_absentee_gets_a_real_task(self):
        session = self._session(self.tracked_mt)
        AttendanceSessionMember.objects.create(session=session, member=self.member_present)
        call_command("check_absences")

        self.assertFalse(MemberFollowUpTask.objects.filter(member=self.member_present).exists(),
            "A checked-in member must never get a follow-up task.")
        task = MemberFollowUpTask.objects.get(member=self.member_absent)
        self.assertEqual(task.assigned_to, self.shepherd)
        self.assertEqual(task.missed_meeting_name, "Friday Worship Service")
        self.assertEqual(task.missed_session, session)
        self.assertFalse(task.done)

    def test_task_assigned_to_none_when_member_has_no_shepherd(self):
        unshepherded = Member.objects.create(surname="Karim", first_name="Ali", location=self.bahrain,
            joined_date=datetime.date(2023, 1, 1))  # no assigned_to
        self._session(self.tracked_mt)
        call_command("check_absences")
        task = MemberFollowUpTask.objects.get(member=unshepherded)
        self.assertIsNone(task.assigned_to)

    # --- The timing threshold is real, not decorative ---

    def test_session_not_yet_past_threshold_is_untouched(self):
        recent_start = timezone.localtime(self.now - datetime.timedelta(hours=1)).time().replace(microsecond=0)
        mt = MeetingType.objects.create(id="wed-rev", name="Wednesday Revival", day="Wednesday",
            frequency="weekly", detail_level="detailed", counts_for_absence=True, start_time=recent_start)
        self._session(mt)
        call_command("check_absences")
        self.assertEqual(MemberFollowUpTask.objects.count(), 0,
            "A session whose meeting started only 1 hour ago (threshold is 3) must not be processed yet.")

    # --- Two real gating conditions ---

    def test_meeting_type_not_marked_counts_for_absence_is_never_processed(self):
        self._session(self.untracked_mt)
        call_command("check_absences")
        self.assertEqual(MemberFollowUpTask.objects.count(), 0)

    def test_meeting_type_with_no_start_time_is_never_processed_even_if_flagged(self):
        old_session = AttendanceSession.objects.create(
            meeting_type=self.no_start_time_mt, date=self.now.date() - datetime.timedelta(days=30),
            location=self.bahrain, mode="in-person", status="pending",
        )
        call_command("check_absences")
        self.assertEqual(MemberFollowUpTask.objects.count(), 0,
            "counts_for_absence=True with no start_time must not be guessed at , simply never checked.")

    # --- Idempotency: safe to re-run without duplicating ---

    def test_rerunning_on_the_same_session_does_not_duplicate(self):
        self._session(self.tracked_mt)
        call_command("check_absences")
        call_command("check_absences")
        call_command("check_absences")
        self.assertEqual(
            MemberFollowUpTask.objects.filter(member=self.member_absent).count(), 1,
            "Running the command multiple times must not create duplicate tasks for the same session.",
        )

    # --- The confirmed "don't stack tasks" rule, and its correct limit ---

    def test_second_different_session_absence_does_not_stack_while_first_is_open(self):
        session1 = self._session(self.tracked_mt, date=self.now.date() - datetime.timedelta(days=7))
        call_command("check_absences")
        self.assertEqual(MemberFollowUpTask.objects.filter(member=self.member_absent).count(), 1)

        session2 = self._session(self.tracked_mt, date=self.now.date())
        call_command("check_absences")
        self.assertEqual(
            MemberFollowUpTask.objects.filter(member=self.member_absent).count(), 1,
            "A second, still-open task must not stack on top of an unresolved first one.",
        )

    def test_new_absence_after_prior_task_resolved_creates_a_genuinely_new_task(self):
        """The distinction that actually matters: 'don't stack' should
        block piling up open tasks, not block real, separate follow-ups
        once the earlier one is actually resolved."""
        session1 = self._session(self.tracked_mt, date=self.now.date() - datetime.timedelta(days=7))
        call_command("check_absences")
        first_task = MemberFollowUpTask.objects.get(member=self.member_absent)
        first_task.done = True
        first_task.contact_method = "Phone call"
        first_task.contact_date = timezone.localdate()
        first_task.save()

        session2 = self._session(self.tracked_mt, date=self.now.date())
        call_command("check_absences")
        tasks = MemberFollowUpTask.objects.filter(member=self.member_absent)
        self.assertEqual(tasks.count(), 2, "A resolved prior task must not block a genuinely new absence.")
        self.assertTrue(tasks.filter(missed_session=session2, done=False).exists())

    # --- No location restriction, matching the rest of this app's rule ---

    def test_only_processes_members_at_the_sessions_own_location(self):
        others = Location.objects.create(id="others", name="Others", note="Qatar")
        qatar_member = Member.objects.create(surname="Yusuf", first_name="Amina", location=others,
            joined_date=datetime.date(2023, 1, 1))
        self._session(self.tracked_mt)  # Bahrain session
        call_command("check_absences")
        self.assertFalse(MemberFollowUpTask.objects.filter(member=qatar_member).exists(),
            "A Bahrain session's roster must not include members from a different location.")
