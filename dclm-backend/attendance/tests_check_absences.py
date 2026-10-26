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
        started = timezone.localtime(self.now - datetime.timedelta(hours=5))
        past_start = started.time().replace(microsecond=0)
        # The local date the service started on, which is yesterday when
        # the tests run in the small hours.
        self.service_date = started.date()
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

    def _session(self, meeting_type, date=None, tick=False):
        s = AttendanceSession.objects.create(
            meeting_type=meeting_type, date=date or self.service_date,
            location=self.bahrain, mode="in-person", status="pending",
        )
        if tick:
            # Names were taken: somebody is ticked present. Since review item
            # O3 a service with nobody ticked is never treated as everyone
            # absent.
            AttendanceSessionMember.objects.create(session=s, member=self.member_present)
        return s

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
        self._session(self.tracked_mt, tick=True)
        call_command("check_absences")
        task = MemberFollowUpTask.objects.get(member=unshepherded)
        self.assertIsNone(task.assigned_to)

    def test_a_service_with_nobody_ticked_chases_nobody(self):
        """Review item O3: a Pending service with no names used to count
        everyone expected as absent. It now shows Names not taken."""
        self._session(self.tracked_mt)
        call_command("check_absences")
        self.assertEqual(MemberFollowUpTask.objects.count(), 0)

    def test_did_not_hold_is_never_checked(self):
        s = self._session(self.tracked_mt, tick=True)
        AttendanceSession.objects.filter(pk=s.pk).update(status="did-not-hold")
        call_command("check_absences")
        self.assertEqual(MemberFollowUpTask.objects.count(), 0)

    # --- The timing threshold is real, not decorative ---

    def test_session_not_yet_past_threshold_is_untouched(self):
        began = timezone.localtime(self.now - datetime.timedelta(hours=1))
        recent_start = began.time().replace(microsecond=0)
        mt = MeetingType.objects.create(id="wed-rev", name="Wednesday Revival", day="Wednesday",
            frequency="weekly", detail_level="detailed", counts_for_absence=True, start_time=recent_start)
        self._session(mt, date=began.date())
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
        self._session(self.tracked_mt, tick=True)
        call_command("check_absences")
        call_command("check_absences")
        call_command("check_absences")
        self.assertEqual(
            MemberFollowUpTask.objects.filter(member=self.member_absent).count(), 1,
            "Running the command multiple times must not create duplicate tasks for the same session.",
        )

    # --- Tasks pile (Kay, 26 October 2026) ---

    def test_a_second_missed_service_gets_its_own_task_while_the_first_is_open(self):
        session1 = self._session(self.tracked_mt, date=self.service_date - datetime.timedelta(days=7), tick=True)
        call_command("check_absences")
        self.assertEqual(MemberFollowUpTask.objects.filter(member=self.member_absent).count(), 1)

        session2 = self._session(self.tracked_mt, date=self.service_date, tick=True)
        call_command("check_absences")
        tasks = MemberFollowUpTask.objects.filter(member=self.member_absent, done=False)
        self.assertEqual(tasks.count(), 2, "Every missed service gets its own task, even with one still open.")
        self.assertEqual(tasks.get(missed_session=session2).missed_in_row, 2)

    def test_new_absence_after_prior_task_resolved_creates_a_genuinely_new_task(self):
        """The distinction that actually matters: 'don't stack' should
        block piling up open tasks, not block real, separate follow-ups
        once the earlier one is actually resolved."""
        session1 = self._session(self.tracked_mt, date=self.service_date - datetime.timedelta(days=7), tick=True)
        call_command("check_absences")
        first_task = MemberFollowUpTask.objects.get(member=self.member_absent)
        first_task.done = True
        first_task.contact_method = "Phone call"
        first_task.contact_date = timezone.localdate()
        first_task.save()

        session2 = self._session(self.tracked_mt, date=self.service_date, tick=True)
        call_command("check_absences")
        tasks = MemberFollowUpTask.objects.filter(member=self.member_absent)
        self.assertEqual(tasks.count(), 2, "A resolved prior task must not block a genuinely new absence.")
        self.assertTrue(tasks.filter(missed_session=session2, done=False).exists())

    # --- No location restriction, matching the rest of this app's rule ---

    def test_only_processes_members_at_the_sessions_own_location(self):
        others = Location.objects.create(id="others", name="Others", note="Qatar")
        qatar_member = Member.objects.create(surname="Yusuf", first_name="Amina", location=others,
            joined_date=datetime.date(2023, 1, 1))
        self._session(self.tracked_mt, tick=True)  # Bahrain session
        call_command("check_absences")
        self.assertFalse(MemberFollowUpTask.objects.filter(member=qatar_member).exists(),
            "A Bahrain session's roster must not include members from a different location.")


class HeadcountSavedEarlyTestCase(CheckAbsencesCommandTestCase):
    """The gap found on 17 Oct 2026: a session whose headcount was saved
    before the check ran was skipped for good, so nobody absent from it
    was ever followed up."""

    def _filled(self, date=None):
        s = self._session(self.tracked_mt, date)
        AttendanceSession.objects.filter(pk=s.pk).update(status="filled", men=40)
        return s

    def test_saved_early_with_names_taken_still_follows_up_absentees(self):
        s = self._filled()
        AttendanceSessionMember.objects.create(session=s, member=self.member_present)
        call_command("check_absences", verbosity=0)
        self.assertFalse(MemberFollowUpTask.objects.filter(member=self.member_present).exists())
        self.assertEqual(MemberFollowUpTask.objects.get(member=self.member_absent).missed_session, s)
        call_command("check_absences", verbosity=0)
        self.assertEqual(MemberFollowUpTask.objects.count(), 1)

    def test_a_headcount_alone_says_nothing_about_who_came(self):
        self._filled()
        call_command("check_absences", verbosity=0)
        self.assertEqual(MemberFollowUpTask.objects.count(), 0)

    def test_newcomers_checked_in_alone_do_not_count_as_names_taken(self):
        from newcomers.models import Newcomer, NewcomerSource
        s = self._filled()
        n = Newcomer.objects.create(name="Abel", source=NewcomerSource.objects.create(name="Friend"),
                                    location=self.bahrain, created_at=self.service_date, stage_since=self.service_date)
        AttendanceSessionMember.objects.create(session=s, newcomer=n)
        call_command("check_absences", verbosity=0)
        self.assertEqual(MemberFollowUpTask.objects.count(), 0)

    def test_old_saved_services_are_left_alone(self):
        s = self._filled(self.service_date - datetime.timedelta(days=8))
        AttendanceSessionMember.objects.create(session=s, member=self.member_present)
        call_command("check_absences", verbosity=0)
        self.assertEqual(MemberFollowUpTask.objects.count(), 0)

    def test_saved_early_but_not_yet_three_hours_after_the_start(self):
        later = timezone.localtime(self.now - datetime.timedelta(hours=1)).time().replace(microsecond=0)
        MeetingType.objects.filter(pk=self.tracked_mt.pk).update(start_time=later)
        s = self._filled(timezone.localtime(self.now - datetime.timedelta(hours=1)).date())
        AttendanceSessionMember.objects.create(session=s, member=self.member_present)
        call_command("check_absences", verbosity=0)
        self.assertEqual(MemberFollowUpTask.objects.count(), 0)
