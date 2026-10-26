"""
Build 1 of the follow-up plan (Kay, 26 October 2026): Follow-up Rules,
meetings made on their day and only where held, the status words, Did not
hold, and refusing a duplicate session.
"""
import datetime
from unittest import mock

from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import AuditLog, Role, RolePermission, User
from core.followup_rules import clock_start, names_deadline, session_state
from core.models import FollowUpRules, Location
from members.models import Member
from .models import AttendanceSession, AttendanceSessionMember, MeetingType

WEEKDAYS = MeetingType.WEEKDAYS


class Base(APITestCase):
    def setUp(self):
        self.bh = Location.objects.create(id="bahrain", name="Bahrain HQ", is_core=True)
        self.qa = Location.objects.create(id="others", name="Qatar")
        role = Role.objects.create(name="Administrator")
        for mod in ["attendance", "admin", "members"]:
            RolePermission.objects.create(role=role, module=mod, can_view=True, can_create=True,
                                          can_edit=True, can_delete=True)
        self.role = role
        self.admin = User.objects.create_user(email="a@t.com", password="x", role=role, first_name="Chinedu",
                                              last_name="Uguru")
        self.qatar_admin = User.objects.create_user(email="q@t.com", password="x", role=role, location=self.qa)
        self.client.force_authenticate(self.admin)
        self.today = timezone.localdate()

    def meeting(self, mid, day, **kw):
        return MeetingType.objects.create(id=mid, name=mid.title(), day=day, frequency="weekly",
                                          detail_level="detailed", **kw)

    def day_after(self, n):
        return WEEKDAYS[(self.today.weekday() + n) % 7]


class MadeOnTheDay(Base):
    def test_a_meeting_today_is_made_today(self):
        mt = self.meeting("today-mt", self.day_after(0))
        call_command("generate_recurring_sessions", verbosity=0)
        self.assertEqual(set(mt.sessions.values_list("date", flat=True)), {self.today})
        self.assertEqual(mt.sessions.count(), 2)  # none ticked means every location

    def test_a_meeting_tomorrow_waits_for_its_day(self):
        mt = self.meeting("tomorrow-mt", self.day_after(1))
        call_command("generate_recurring_sessions", verbosity=0)
        self.assertFalse(mt.sessions.exists())

    def test_days_ahead_brings_it_forward(self):
        mt = self.meeting("ahead-mt", self.day_after(2), create_days_ahead=2)
        call_command("generate_recurring_sessions", verbosity=0)
        self.assertEqual(list(mt.sessions.values_list("date", flat=True).distinct()),
                         [self.today + datetime.timedelta(days=2)])

    def test_only_where_it_is_held(self):
        mt = self.meeting("held-mt", self.day_after(0))
        mt.held_at.set([self.bh])
        call_command("generate_recurring_sessions", verbosity=0)
        self.assertEqual(list(mt.sessions.values_list("location_id", flat=True)), ["bahrain"])

    def test_a_new_location_joins_meetings_held_everywhere(self):
        everywhere = self.meeting("all-mt", "Friday")
        everywhere.held_at.set([self.bh, self.qa])
        some = self.meeting("some-mt", "Monday")
        some.held_at.set([self.bh])
        r = self.client.post("/api/locations/", {"id": "kuwait", "name": "Kuwait"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertIn("kuwait", everywhere.held_at.values_list("id", flat=True))
        self.assertNotIn("kuwait", some.held_at.values_list("id", flat=True))


class MeetingSettings(Base):
    def test_start_time_days_ahead_and_held_at_are_saved(self):
        self.meeting("fri-worship", "Friday", counts_for_absence=True)
        r = self.client.patch("/api/meeting-types/fri-worship/",
                              {"start_time": "18:00", "create_days_ahead": 1, "held_at": ["bahrain"]}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual((r.data["start_time"], r.data["create_days_ahead"], r.data["held_at_names"]),
                         ("18:00:00", 1, ["Bahrain HQ"]))
        self.assertEqual(r.data["setup_warnings"], [])

    def test_too_many_days_ahead_is_refused_with_a_reason(self):
        self.meeting("fri-worship", "Friday")
        r = self.client.patch("/api/meeting-types/fri-worship/", {"create_days_ahead": 20}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("at most 14 days", str(r.data))

    def test_a_tracked_meeting_with_no_start_time_says_so(self):
        self.meeting("sat-workers", "Saturday", counts_for_absence=True)
        r = self.client.get("/api/meeting-types/sat-workers/")
        self.assertIn("has no start time", r.data["setup_warnings"][0])


class StatusWords(Base):
    def setUp(self):
        super().setUp()
        self.fri = self.meeting("fri-worship", "Friday", counts_for_absence=True, start_time=datetime.time(18, 0))
        self.mon = self.meeting("mon-bs", "Monday")
        self.member = Member.objects.create(first_name="Joshua", surname="Afari", location=self.bh,
                                            joined_date=datetime.date(2020, 1, 1))

    def session(self, mt, day, **kw):
        return AttendanceSession.objects.create(meeting_type=mt, date=day, location=self.bh, mode="in-person", **kw)

    def state(self, s, now):
        return session_state(AttendanceSession.objects.get(pk=s.pk), now=now)

    def test_each_word(self):
        day = datetime.date(2026, 10, 30)
        before = timezone.make_aware(datetime.datetime(2026, 10, 29, 12))
        on_day = timezone.make_aware(datetime.datetime(2026, 10, 30, 20))
        next_evening = timezone.make_aware(datetime.datetime(2026, 10, 31, 18, 30))
        s = self.session(self.fri, day)
        self.assertEqual(self.state(s, before), "upcoming")
        self.assertEqual(self.state(s, on_day), "waiting-names")
        self.assertEqual(self.state(s, next_evening), "names-not-taken")
        AttendanceSession.objects.filter(pk=s.pk).update(status="filled", men=40)
        self.assertEqual(self.state(s, next_evening), "names-not-taken")   # a headcount alone
        AttendanceSessionMember.objects.create(session=s, member=self.member)
        self.assertEqual(self.state(s, next_evening), "done")
        AttendanceSession.objects.filter(pk=s.pk).update(status="did-not-hold")
        self.assertEqual(self.state(s, next_evening), "did-not-hold")

    def test_a_headcount_meeting_uses_plain_words(self):
        day = datetime.date(2026, 11, 2)
        s = self.session(self.mon, day)
        self.assertEqual(self.state(s, timezone.make_aware(datetime.datetime(2026, 11, 2, 20))), "waiting")
        self.assertEqual(self.state(s, timezone.make_aware(datetime.datetime(2026, 11, 3, 19))), "not-filled")

    def test_the_list_carries_the_word_and_pending_counts_only_days_that_came(self):
        self.session(self.fri, self.today + datetime.timedelta(days=3))
        self.session(self.mon, self.today - datetime.timedelta(days=1))
        rows = self.client.get("/api/attendance-sessions/").data["results"]
        self.assertIn("Upcoming", [r["state_label"] for r in rows])
        self.assertEqual(self.client.get("/api/attendance-sessions/stats/").data["pending"], 1)


class DidNotHold(StatusWords):
    def url(self, s):
        return f"/api/attendance-sessions/{s.id}/did-not-hold/"

    def test_marking_and_undoing(self):
        s = self.session(self.fri, self.today - datetime.timedelta(days=1))
        self.assertIn("Say why", str(self.client.post(self.url(s), {}, format="json").data))
        r = self.client.post(self.url(s), {"reason": "Public holiday"}, format="json")
        self.assertEqual((r.status_code, r.data["state"], r.data["not_held_reason"]), (200, "did-not-hold", "Public holiday"))
        self.assertTrue(AuditLog.objects.filter(action="Marked Did not hold").exists())
        r = self.client.post(f"/api/attendance-sessions/{s.id}/check_in/", {"member_id": self.member.id}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("Did not hold", r.data["detail"])
        r = self.client.delete(self.url(s))
        self.assertEqual(r.data["status"], "pending")

    def test_refused_before_its_day_or_once_attendance_is_recorded(self):
        future = self.session(self.fri, self.today + datetime.timedelta(days=2))
        self.assertEqual(self.client.post(self.url(future), {"reason": "x"}, format="json").status_code, 400)
        done = self.session(self.mon, self.today - datetime.timedelta(days=1), status="filled")
        r = self.client.post(self.url(done), {"reason": "x"}, format="json")
        self.assertIn("already recorded", r.data["detail"])


class NoDuplicates(StatusWords):
    def test_a_second_session_is_refused_and_names_the_first(self):
        s = self.session(self.fri, self.today)
        r = self.client.post("/api/attendance-sessions/", {"meeting_type": "fri-worship", "date": str(self.today),
                                                            "location": "bahrain", "mode": "in-person"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("already exists", str(r.data["detail"]))
        self.assertEqual(int(str(r.data["existing_id"][0]) if isinstance(r.data["existing_id"], list)
                             else r.data["existing_id"]), s.id)


class Rules(Base):
    def test_everyone_reads_the_decided_values(self):
        r = self.client.get("/api/followup-rules/")
        self.assertEqual((r.data["clock_start"], r.data["due_hours"], r.data["reason_hours"], r.data["review_days"],
                          r.data["decide_days"], r.data["shepherd_limit"], r.data["newcomer_stages"]),
                         ("18:00:00", 24, 48, 3, 5, 6, ["new", "contacted", "attending"]))
        self.assertTrue(r.data["can_change"])

    def test_change_is_logged_and_can_be_put_back(self):
        r = self.client.patch("/api/followup-rules/", {"shepherd_limit": 8, "newcomer_stages": ["attending"]},
                              format="json")
        self.assertEqual((r.status_code, r.data["shepherd_limit"], r.data["newcomer_stages"]), (200, 8, ["attending"]))
        self.assertIn("shepherd_limit: 6 to 8", AuditLog.objects.get(entity_type="Follow-up Rules").details)
        r = self.client.post("/api/followup-rules/")
        self.assertEqual(r.data["shepherd_limit"], 6)

    def test_rules_that_contradict_each_other_are_explained(self):
        r = self.client.patch("/api/followup-rules/", {"reason_hours": 12}, format="json")
        self.assertIn("more hours than Follow-up due after", str(r.data["reason_hours"]))
        r = self.client.patch("/api/followup-rules/", {"decide_days": 2}, format="json")
        self.assertIn("more days than the Review list", str(r.data["decide_days"]))
        r = self.client.patch("/api/followup-rules/", {"shepherd_limit": 0}, format="json")
        self.assertIn("from 1 to 50", str(r.data["shepherd_limit"]))

    def test_one_location_cannot_change_rules_for_all(self):
        self.client.force_authenticate(self.qatar_admin)
        r = self.client.patch("/api/followup-rules/", {"shepherd_limit": 9}, format="json")
        self.assertEqual(r.status_code, 403)
        self.assertIn("All locations", r.data["detail"])
        self.assertFalse(self.client.get("/api/followup-rules/").data["can_change"])


class Clock(Base):
    def test_normal_and_late_starts(self):
        fri = self.meeting("fri-worship", "Friday", start_time=datetime.time(18, 0))
        day = datetime.date(2026, 10, 30)
        six = timezone.make_aware(datetime.datetime(2026, 10, 30, 18))
        made_by_check = timezone.make_aware(datetime.datetime(2026, 10, 30, 21, 17))
        made_late = timezone.make_aware(datetime.datetime(2026, 11, 1, 10))
        self.assertEqual(clock_start(day, made_by_check, fri), six)
        self.assertEqual(clock_start(day, made_late, fri), made_late)
        self.assertEqual(names_deadline(day), timezone.make_aware(datetime.datetime(2026, 10, 31, 18)))
