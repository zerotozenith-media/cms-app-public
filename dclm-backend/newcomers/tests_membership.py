"""
Tests for the membership journey: audience scoping, the readiness rule,
conversion to a member, and contact attempts.
"""
import datetime

from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Role, RolePermission, User
from attendance.models import AttendanceSession, AttendanceSessionMember, MeetingType
from core.models import Location
from members.models import Member, MemberFollowUpTask
from newcomers.membership import readiness
from newcomers.models import (
    MilestoneType, Newcomer, NewcomerContactAttempt, NewcomerMilestone, NewcomerSource,
)


class Base(APITestCase):
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        role = Role.objects.create(name="Administrator")
        for module in ["members", "attendance", "newcomers", "finance",
                       "goals", "reports", "outreach", "admin"]:
            RolePermission.objects.create(
                role=role, module=module,
                can_view=True, can_create=True, can_edit=True, can_delete=True)
        self.admin = User.objects.create_user(email="admin@t.com", password="x", role=role)
        self.client.force_authenticate(user=self.admin)
        self.source = NewcomerSource.objects.create(name="Invited by a member")
        self.today = timezone.localdate()

    def member(self, first, category=Member.Category.GENERAL, leader=False):
        return Member.objects.create(
            surname="Test", first_name=first, location=self.bahrain,
            joined_date=datetime.date(2020, 1, 1), category=category, is_leader=leader)

    def newcomer(self, name="Joy Mensah", stage=Newcomer.Stage.ATTENDING):
        return Newcomer.objects.create(
            name=name, source=self.source, location=self.bahrain, stage=stage,
            created_at=self.today, stage_since=self.today)

    def friday(self, offset_days):
        mt, _ = MeetingType.objects.get_or_create(
            id="fri-worship", defaults=dict(
                name="Friday Worship Service", day="Friday", frequency="weekly",
                detail_level="detailed", counts_for_absence=True,
                start_time=datetime.time(18, 0)))
        return AttendanceSession.objects.create(
            meeting_type=mt, date=self.today - datetime.timedelta(days=offset_days),
            location=self.bahrain, mode="in-person", status="pending")


class AudienceTestCase(Base):
    """
    Who is chased when a meeting counts toward absence follow-up.

    Without this, switching absence tracking on for a workers meeting
    created a task for every general member who was never expected there.
    """
    def _workers_meeting(self):
        return MeetingType.objects.create(
            id="sat-workers", name="Saturday Workers Meeting", day="Saturday",
            frequency="weekly", detail_level="simple",
            counts_for_absence=True, start_time=datetime.time(10, 0),
            audience=MeetingType.Audience.WORKERS)

    def test_a_workers_meeting_only_chases_workers(self):
        worker = self.member("Worker", Member.Category.WORKER)
        self.member("General")
        self.member("InTraining", Member.Category.IN_TRAINING)

        mt = self._workers_meeting()
        AttendanceSession.objects.create(
            meeting_type=mt, date=self.today - datetime.timedelta(days=1),
            location=self.bahrain, mode="in-person", status="pending")
        call_command("check_absences", verbosity=0)

        chased = {t.member.first_name for t in MemberFollowUpTask.objects.all()}
        self.assertEqual(chased, {"Worker"})

    def test_workers_in_training_are_not_workers(self):
        """They are a progression marker, not a level of responsibility."""
        self.member("InTraining", Member.Category.IN_TRAINING)
        mt = self._workers_meeting()
        AttendanceSession.objects.create(
            meeting_type=mt, date=self.today - datetime.timedelta(days=1),
            location=self.bahrain, mode="in-person", status="pending")
        call_command("check_absences", verbosity=0)
        self.assertEqual(MemberFollowUpTask.objects.count(), 0)

    def test_a_leadership_meeting_only_chases_leaders(self):
        self.member("Leader", Member.Category.WORKER, leader=True)
        self.member("PlainWorker", Member.Category.WORKER)
        mt = MeetingType.objects.create(
            id="tue-leadership", name="Tuesday Leadership Development", day="Tuesday",
            frequency="weekly", detail_level="simple",
            counts_for_absence=True, start_time=datetime.time(19, 0),
            audience=MeetingType.Audience.LEADERSHIP)
        AttendanceSession.objects.create(
            meeting_type=mt, date=self.today - datetime.timedelta(days=1),
            location=self.bahrain, mode="in-person", status="pending")
        call_command("check_absences", verbosity=0)
        chased = {t.member.first_name for t in MemberFollowUpTask.objects.all()}
        self.assertEqual(chased, {"Leader"})

    def test_everyone_still_means_everyone(self):
        self.member("A")
        self.member("B", Member.Category.WORKER)
        self.friday(1)
        call_command("check_absences", verbosity=0)
        self.assertEqual(MemberFollowUpTask.objects.count(), 2)

    def test_leadership_is_a_flag_not_a_category(self):
        leader = self.member("Leader", Member.Category.WORKER, leader=True)
        self.assertEqual(leader.category, Member.Category.WORKER)
        self.assertTrue(leader.is_leader)


class ReadinessTestCase(Base):
    """
    Proposed for membership, never promoted automatically.
    """
    def _attend(self, newcomer, sessions):
        for s in sessions:
            AttendanceSessionMember.objects.create(session=s, newcomer=newcomer)

    def _saved(self, newcomer, when=None):
        salvation, _ = MilestoneType.objects.get_or_create(name="Salvation")
        NewcomerMilestone.objects.create(
            newcomer=newcomer, milestone_type=salvation,
            achieved_date=when or self.today)

    def test_all_three_conditions_together_propose_someone(self):
        n = self.newcomer()
        sessions = [self.friday(d) for d in range(200, 0, -7)]
        self._attend(n, sessions[:len(sessions) // 2 + 2])
        self._saved(n)
        r = readiness(n)
        self.assertTrue(r["attendance_met"])
        self.assertTrue(r["time_met"])
        self.assertTrue(r["has_salvation"])
        self.assertTrue(r["ready"])

    def test_good_attendance_is_not_enough_without_salvation(self):
        n = self.newcomer()
        sessions = [self.friday(d) for d in range(200, 0, -7)]
        self._attend(n, sessions)
        self.assertFalse(readiness(n)["ready"])

    def test_salvation_is_not_enough_without_the_six_months(self):
        """This one bites in practice: someone attending well for three
        months with salvation recorded is still not proposed."""
        n = self.newcomer()
        sessions = [self.friday(d) for d in range(60, 0, -7)]
        self._attend(n, sessions)
        self._saved(n)
        r = readiness(n)
        self.assertTrue(r["attendance_met"])
        self.assertTrue(r["has_salvation"])
        self.assertFalse(r["time_met"])
        self.assertFalse(r["ready"])

    def test_poor_attendance_is_not_enough(self):
        n = self.newcomer()
        sessions = [self.friday(d) for d in range(200, 0, -7)]
        self._attend(n, sessions[:3])
        self._saved(n)
        r = readiness(n)
        self.assertFalse(r["attendance_met"])
        self.assertFalse(r["ready"])

    def test_a_milestone_with_no_date_does_not_count(self):
        """A row with no date is the checklist item existing, not the
        thing having happened."""
        n = self.newcomer()
        salvation, _ = MilestoneType.objects.get_or_create(name="Salvation")
        NewcomerMilestone.objects.create(newcomer=n, milestone_type=salvation)
        self.assertFalse(readiness(n)["has_salvation"])

    def test_someone_who_never_attended_is_handled(self):
        r = readiness(self.newcomer(stage=Newcomer.Stage.NEW))
        self.assertIsNone(r["first_attended"])
        self.assertEqual(r["attendance_percent"], 0)
        self.assertFalse(r["ready"])

    def test_the_percentage_counts_services_held_since_they_started(self):
        """Not every service ever, or someone who joined last month would
        look far worse than they are."""
        n = self.newcomer()
        old = [self.friday(d) for d in range(400, 300, -7)]   # before they came
        recent = [self.friday(d) for d in range(60, 0, -7)]
        self._attend(n, recent)
        r = readiness(n)
        self.assertEqual(r["services_held"], len(recent))
        self.assertEqual(r["attendance_percent"], 100)


class MakeMemberTestCase(Base):
    def test_converting_creates_a_linked_member(self):
        n = self.newcomer()
        resp = self.client.post(f"/api/newcomers/{n.id}/make-member/")
        self.assertEqual(resp.status_code, 201)
        member = Member.objects.get(from_newcomer=n)
        self.assertEqual(member.first_name, "Joy")

    def test_the_newcomer_record_is_kept(self):
        """Deleting it would destroy how they arrived and their whole
        follow-up history."""
        n = self.newcomer()
        self.client.post(f"/api/newcomers/{n.id}/make-member/")
        self.assertTrue(Newcomer.objects.filter(id=n.id).exists())

    def test_their_card_moves_to_the_member_column(self):
        n = self.newcomer()
        self.client.post(f"/api/newcomers/{n.id}/make-member/")
        n.refresh_from_db()
        self.assertEqual(n.stage, Newcomer.Stage.MEMBER)

    def test_the_move_is_recorded_in_their_history(self):
        n = self.newcomer()
        self.client.post(f"/api/newcomers/{n.id}/make-member/")
        self.assertTrue(n.status_history.filter(stage=Newcomer.Stage.MEMBER).exists())

    def test_nobody_is_added_twice(self):
        n = self.newcomer()
        self.client.post(f"/api/newcomers/{n.id}/make-member/")
        resp = self.client.post(f"/api/newcomers/{n.id}/make-member/")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(Member.objects.filter(from_newcomer=n).count(), 1)

    def test_anyone_can_be_made_a_member_regardless_of_the_rule(self):
        """Covers someone relocating from another church where they were
        already established."""
        n = self.newcomer(stage=Newcomer.Stage.NEW)
        self.assertFalse(readiness(n)["ready"])
        self.assertEqual(self.client.post(f"/api/newcomers/{n.id}/make-member/").status_code, 201)


class ContactAttemptTestCase(Base):
    def test_an_attempt_can_be_logged(self):
        n = self.newcomer()
        resp = self.client.post(f"/api/newcomers/{n.id}/log-attempt/",
                                {"method": "Phone call", "note": "Left a voice note"})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(NewcomerContactAttempt.objects.count(), 1)

    def test_an_unknown_method_is_refused(self):
        n = self.newcomer()
        resp = self.client.post(f"/api/newcomers/{n.id}/log-attempt/", {"method": "Telepathy"})
        self.assertEqual(resp.status_code, 400)

    def test_attempts_appear_in_the_journey(self):
        """Without them the record flatters the work: three unanswered
        calls would look like nobody tried."""
        n = self.newcomer()
        self.client.post(f"/api/newcomers/{n.id}/log-attempt/", {"method": "Phone call"})
        journey = self.client.get(f"/api/newcomers/{n.id}/journey/").data
        self.assertTrue(any(e["kind"] == "attempt" for e in journey))


class JourneyTestCase(Base):
    def test_the_journey_is_in_date_order(self):
        n = self.newcomer()
        self.client.post(f"/api/newcomers/{n.id}/log-attempt/", {"method": "Phone call"})
        journey = self.client.get(f"/api/newcomers/{n.id}/journey/").data
        dates = [e["date"] for e in journey]
        self.assertEqual(dates, sorted(dates))

    def test_registration_always_appears(self):
        n = self.newcomer()
        journey = self.client.get(f"/api/newcomers/{n.id}/journey/").data
        self.assertTrue(any(e["kind"] == "registered" for e in journey))

    def test_becoming_a_member_appears(self):
        n = self.newcomer()
        self.client.post(f"/api/newcomers/{n.id}/make-member/")
        journey = self.client.get(f"/api/newcomers/{n.id}/journey/").data
        self.assertTrue(any(e["kind"] == "member" for e in journey))

    def test_readiness_is_reachable_from_the_api(self):
        n = self.newcomer()
        resp = self.client.get(f"/api/newcomers/{n.id}/readiness/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("attendance_percent", resp.data)
