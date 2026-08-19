"""
Tests for follow-up notifications.

The behaviour that matters here is mostly about restraint: not emailing
people who have nothing waiting, not emailing at all when nothing has
happened, and never letting one bad address stop everyone else's mail.
"""
import datetime

from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from io import StringIO

from accounts.models import Role, RolePermission, User
from attendance.models import MeetingType, AttendanceSession
from core.digests import build_shepherd_digest, build_leadership_summary
from core.models import Location
from members.models import Member, MemberFollowUpTask


@override_settings(NOTIFICATIONS_ENABLED=True, APP_BASE_URL="https://cms.example.org")
class FollowUpDigestTestCase(TestCase):
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)

        self.admin_role = Role.objects.create(name="Administrator")
        RolePermission.objects.create(role=self.admin_role, module="admin", can_view=True)
        self.worker_role = Role.objects.create(name="Worker")
        RolePermission.objects.create(role=self.worker_role, module="members", can_view=True)

        self.admin = User.objects.create_user(
            email="admin@example.org", password="x", role=self.admin_role)

        shepherd_member = Member.objects.create(
            surname="Osei", first_name="Sarah", location=self.bahrain,
            joined_date=datetime.date(2017, 1, 1), category=Member.Category.WORKER)
        self.shepherd = User.objects.create_user(
            email="sarah@example.org", password="x", role=self.worker_role)
        self.shepherd.member = shepherd_member
        self.shepherd.save()

        self.today = timezone.localdate()
        self.meeting = MeetingType.objects.create(
            id="fri-worship", name="Friday Worship Service", day="Friday",
            frequency="weekly", detail_level="detailed",
            counts_for_absence=True, start_time="18:00")
        AttendanceSession.objects.create(
            meeting_type=self.meeting, date=self.today, location=self.bahrain,
            mode="in-person", status="pending")

    def _task(self, first, due_offset=0, assigned=True, done=False):
        member = Member.objects.create(
            surname="Member", first_name=first, location=self.bahrain,
            joined_date=datetime.date(2024, 1, 1), category=Member.Category.GENERAL)
        return MemberFollowUpTask.objects.create(
            member=member, text="Missed service",
            due_date=self.today + datetime.timedelta(days=due_offset),
            assigned_to=self.shepherd if assigned else None,
            done=done,
            missed_meeting_name="Friday Worship Service", missed_date=self.today)

    # ---- what gets sent ----

    def test_shepherd_receives_their_open_tasks(self):
        self._task("Fatima")
        self._task("Tom")
        call_command("send_followup_digests", stdout=StringIO())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["sarah@example.org"])
        self.assertIn("2 follow-ups", mail.outbox[0].subject)

    def test_overdue_is_called_out_in_the_subject(self):
        self._task("Fatima", due_offset=-5)
        call_command("send_followup_digests", stdout=StringIO())
        self.assertIn("overdue", mail.outbox[0].subject)

    def test_nobody_is_emailed_when_they_have_nothing_waiting(self):
        """An email that says "you have no tasks" teaches people to
        ignore the next one."""
        call_command("send_followup_digests", stdout=StringIO())
        self.assertEqual(len(mail.outbox), 0)

    def test_completed_tasks_are_not_included(self):
        self._task("Done", done=True)
        call_command("send_followup_digests", stdout=StringIO())
        self.assertEqual(len(mail.outbox), 0)

    def test_unassigned_tasks_email_nobody_but_are_reported(self):
        self._task("Orphan", assigned=False)
        out = StringIO()
        call_command("send_followup_digests", stdout=out)
        self.assertEqual(len(mail.outbox), 0)
        self.assertIn("nobody assigned", out.getvalue())

    # ---- when it runs ----

    def test_does_nothing_when_no_tracked_service_happened(self):
        AttendanceSession.objects.update(date=self.today - datetime.timedelta(days=10))
        self._task("Fatima")
        call_command("send_followup_digests", stdout=StringIO())
        self.assertEqual(len(mail.outbox), 0)

    def test_force_overrides_the_no_recent_service_guard(self):
        AttendanceSession.objects.update(date=self.today - datetime.timedelta(days=10))
        self._task("Fatima")
        call_command("send_followup_digests", "--force", stdout=StringIO())
        self.assertEqual(len(mail.outbox), 1)

    def test_untracked_meetings_do_not_trigger_a_digest(self):
        """A meeting nobody is expected at should not cause emails."""
        self.meeting.counts_for_absence = False
        self.meeting.save()
        self._task("Fatima")
        call_command("send_followup_digests", stdout=StringIO())
        self.assertEqual(len(mail.outbox), 0)

    def test_dry_run_sends_nothing(self):
        self._task("Fatima")
        call_command("send_followup_digests", "--dry-run", stdout=StringIO())
        self.assertEqual(len(mail.outbox), 0)

    # ---- safety ----

    @override_settings(NOTIFICATIONS_ENABLED=False)
    def test_nothing_is_sent_when_notifications_are_disabled(self):
        """Protects a staging copy of the real database from emailing
        the congregation."""
        self._task("Fatima")
        call_command("send_followup_digests", stdout=StringIO())
        self.assertEqual(len(mail.outbox), 0)

    def test_a_shepherd_with_no_email_is_skipped_not_fatal(self):
        self.shepherd.email = ""
        self.shepherd.save()
        self._task("Fatima")
        call_command("send_followup_digests", stdout=StringIO())  # must not raise
        self.assertEqual(len(mail.outbox), 0)

    # ---- content ----

    def test_digest_uses_the_persons_real_name(self):
        self._task("Fatima")
        call_command("send_followup_digests", stdout=StringIO())
        self.assertIn("Sarah Osei", mail.outbox[0].body)
        self.assertNotIn("@example.org", mail.outbox[0].body)

    def test_digest_returns_none_when_there_are_no_tasks(self):
        self.assertIsNone(build_shepherd_digest("Sarah Osei", []))


@override_settings(NOTIFICATIONS_ENABLED=True, APP_BASE_URL="https://cms.example.org")
class LeadershipSummaryTestCase(TestCase):
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        admin_role = Role.objects.create(name="Administrator")
        RolePermission.objects.create(role=admin_role, module="admin", can_view=True)
        worker_role = Role.objects.create(name="Worker")
        RolePermission.objects.create(role=worker_role, module="members", can_view=True)

        self.admin = User.objects.create_user(
            email="admin@example.org", password="x", role=admin_role)
        self.worker = User.objects.create_user(
            email="worker@example.org", password="x", role=worker_role)

    def test_goes_only_to_people_who_can_see_admin(self):
        call_command("send_leadership_summary", stdout=StringIO())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["admin@example.org"])

    def test_sends_even_when_there_is_nothing_outstanding(self):
        """Unlike the shepherd digest: a quiet week is worth confirming,
        and it proves the notifications still work."""
        call_command("send_leadership_summary", stdout=StringIO())
        self.assertEqual(len(mail.outbox), 1)

    def test_summary_counts_are_correct(self):
        member = Member.objects.create(
            surname="X", first_name="Y", location=self.bahrain,
            joined_date=datetime.date(2024, 1, 1), category=Member.Category.GENERAL)
        today = timezone.localdate()
        MemberFollowUpTask.objects.create(
            member=member, text="t", due_date=today - datetime.timedelta(days=5),
            missed_meeting_name="Friday Worship Service", missed_date=today)

        stats_text = build_leadership_summary(
            {"open": 1, "overdue": 1, "unassigned": 1, "completed_this_week": 0})[1]
        self.assertIn("Open follow-ups:  1", stats_text)
        self.assertIn("nobody assigned", stats_text)

    @override_settings(NOTIFICATIONS_ENABLED=False)
    def test_respects_the_disabled_switch(self):
        call_command("send_leadership_summary", stdout=StringIO())
        self.assertEqual(len(mail.outbox), 0)
