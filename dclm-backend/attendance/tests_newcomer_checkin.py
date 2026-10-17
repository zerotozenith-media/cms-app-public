"""Newcomers checked in by name, so their Friday attendance builds up towards membership."""
import datetime

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Role, RolePermission, User
from attendance.models import AttendanceSession, AttendanceSessionMember, Fellowship, MeetingType
from core.models import Location
from members.models import Member
from newcomers.membership import _months_between, readiness
from newcomers.models import Newcomer, NewcomerSource

D = datetime.date


class Base(APITestCase):
    def setUp(self):
        self.bh = Location.objects.create(id="bahrain", name="Bahrain HQ", is_core=True)
        self.qa = Location.objects.create(id="others", name="Qatar")
        role = Role.objects.create(name="Usher")
        RolePermission.objects.create(role=role, module="attendance", can_view=True, can_create=True, can_edit=True)
        RolePermission.objects.create(role=role, module="newcomers", can_view=True, can_create=True, can_edit=True)
        self.usher = User.objects.create_user(email="u@t.com", password="x", role=role)
        viewer = Role.objects.create(name="Viewer")
        RolePermission.objects.create(role=viewer, module="attendance", can_view=True)
        self.viewer = User.objects.create_user(email="v@t.com", password="x", role=viewer)
        self.client.force_authenticate(self.usher)
        self.fri = MeetingType.objects.create(id="fri-worship", name="Friday Worship Service", day="Friday",
                                              frequency="weekly", detail_level="detailed")
        self.mon = MeetingType.objects.create(id="mon-bs", name="Monday Bible Study", day="Monday",
                                              frequency="weekly", detail_level="detailed")
        self.house = MeetingType.objects.create(id="fri-house", name="Friday House Caring Fellowship", day="Friday",
                                                frequency="weekly", detail_level="detailed")
        self.today = timezone.localdate()
        self.src = NewcomerSource.objects.create(name="Friend")

    def session(self, mt=None, date=None, loc=None, **kw):
        return AttendanceSession.objects.create(meeting_type=mt or self.fri, date=date or self.today,
                                                location=loc or self.bh, mode="in-person", **kw)

    def newcomer(self, name, stage="attending", loc=None, came=None):
        d = came or D(2026, 7, 1)
        return Newcomer.objects.create(name=name, source=self.src, stage=stage, location=loc or self.bh,
                                       created_at=d, stage_since=d)


class CheckIn(Base):
    def url(self, s):
        return f"/api/attendance-sessions/{s.id}/check_in/"

    def test_tap_a_newcomer_in_switch_online_and_out(self):
        s, n = self.session(), self.newcomer("Abel")
        r = self.client.post(self.url(s), {"newcomer_id": n.id}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual([(a["newcomer"], a["newcomer_name"], a["member"]) for a in r.data["attendees"]], [(n.id, "Abel", None)])
        r = self.client.patch(self.url(s), {"newcomer_id": n.id, "mode": "online"}, format="json")
        self.assertEqual(AttendanceSessionMember.objects.get(newcomer=n).mode, "online")
        self.client.delete(self.url(s), {"newcomer_id": n.id}, format="json")
        self.assertFalse(AttendanceSessionMember.objects.filter(newcomer=n).exists())
        # Headcounts stay as they are.
        s.refresh_from_db()
        self.assertEqual((s.total, s.status), (0, "pending"))

    def test_a_member_and_a_newcomer_side_by_side(self):
        s, n = self.session(), self.newcomer("Abel")
        m = Member.objects.create(surname="Afari", first_name="Gloria", location=self.bh, joined_date=D(2026, 7, 1))
        self.client.post(self.url(s), {"member_id": m.id}, format="json")
        r = self.client.post(self.url(s), {"newcomer_id": n.id}, format="json")
        self.assertEqual(len(r.data["attendees"]), 2)
        # A member's undo does not touch the newcomer.
        self.client.delete(self.url(s), {"member_id": m.id}, format="json")
        self.assertTrue(AttendanceSessionMember.objects.filter(newcomer=n).exists())

    def test_one_person_at_a_time_and_only_real_ones(self):
        s, n = self.session(), self.newcomer("Abel")
        self.assertEqual(self.client.post(self.url(s), {}, format="json").status_code, 400)
        self.assertEqual(self.client.post(self.url(s), {"member_id": 1, "newcomer_id": n.id}, format="json").status_code, 400)
        self.assertEqual(self.client.post(self.url(s), {"newcomer_id": 9999}, format="json").status_code, 404)
        self.assertEqual(self.client.post(self.url(s), {"newcomer_id": n.id, "mode": "x"}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(self.url(s), {"newcomer_id": n.id, "mode": "online"}, format="json").status_code, 404)
        later = self.session(date=self.today + datetime.timedelta(days=3))
        self.assertEqual(self.client.post(self.url(later), {"newcomer_id": n.id}, format="json").status_code, 400)
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.post(self.url(s), {"newcomer_id": n.id}, format="json").status_code, 403)

    def test_recording_headcounts_keeps_newcomer_check_ins(self):
        s, n = self.session(), self.newcomer("Abel")
        self.client.post(self.url(s), {"newcomer_id": n.id}, format="json")
        AttendanceSessionMember.objects.filter(session=s, member__isnull=False).delete()
        self.assertTrue(AttendanceSessionMember.objects.filter(session=s, newcomer=n).exists())

    def test_absence_check_ignores_newcomers(self):
        s = self.session()
        AttendanceSessionMember.objects.create(session=s, newcomer=self.newcomer("Abel"))
        call_command("check_absences", verbosity=0)


class Roster(Base):
    def test_who_is_listed(self):
        s = self.session()
        a, b = self.newcomer("Abel"), self.newcomer("Bunmi", stage="new")
        self.newcomer("Member now", stage="member")
        self.newcomer("Not interested", stage="not-interested")
        q = self.newcomer("Qatar visitor", loc=self.qa)
        AttendanceSessionMember.objects.create(session=s, newcomer=q)       # visiting, already checked in
        r = self.client.get(f"/api/attendance-sessions/{s.id}/newcomer-roster/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual([x["name"] for x in r.data["results"]], ["Abel", "Bunmi", "Qatar visitor"])
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.get(f"/api/attendance-sessions/{s.id}/newcomer-roster/").status_code, 403)

    def test_fridays_so_far_on_friday_worship_only(self):
        n = self.newcomer("Abel")
        past = [self.today - datetime.timedelta(days=7 * k) for k in (3, 2, 1)]
        for i, d in enumerate(past):
            s = self.session(date=d, status="filled")
            if i != 1:
                AttendanceSessionMember.objects.create(session=s, newcomer=n)
        s = self.session()
        r = self.client.get(f"/api/attendance-sessions/{s.id}/newcomer-roster/").data
        self.assertTrue(r["fridays"])
        self.assertEqual((r["results"][0]["fridays_attended"], r["results"][0]["fridays_held"]), (2, 4))
        mon = self.session(mt=self.mon)
        r = self.client.get(f"/api/attendance-sessions/{mon.id}/newcomer-roster/").data
        self.assertFalse(r["fridays"])
        self.assertNotIn("fridays_attended", r["results"][0])


class Readiness(TestCase):
    def setUp(self):
        self.bh = Location.objects.create(id="bahrain", name="Bahrain HQ", is_core=True)
        self.fri = MeetingType.objects.create(id="fri-worship", name="Friday Worship Service", day="Friday",
                                              frequency="weekly", detail_level="detailed")
        self.src = NewcomerSource.objects.create(name="Friend")

    def test_six_months_count_from_first_came(self):
        n = Newcomer.objects.create(name="Paschal", source=self.src, stage="attending", location=self.bh,
                                    created_at=D(2026, 7, 1), stage_since=D(2026, 7, 1))
        s = AttendanceSession.objects.create(meeting_type=self.fri, date=D(2026, 10, 16), location=self.bh, mode="in-person")
        AttendanceSessionMember.objects.create(session=s, newcomer=n)
        r = readiness(n, today=D(2026, 12, 31))
        self.assertEqual((r["first_came"], r["first_attended"], r["months_attending"], r["time_met"]),
                         (D(2026, 7, 1), D(2026, 10, 16), 5, False))
        self.assertTrue(readiness(n, today=D(2027, 1, 1))["time_met"])
        # Fridays still count from the first check-in: 1 of 1.
        self.assertEqual(readiness(n, today=D(2027, 1, 1))["attendance_percent"], 100)

    def test_an_earlier_check_in_moves_first_came_back(self):
        n = Newcomer.objects.create(name="Late entry", source=self.src, stage="attending", location=self.bh,
                                    created_at=D(2026, 9, 1), stage_since=D(2026, 9, 1))
        s = AttendanceSession.objects.create(meeting_type=self.fri, date=D(2026, 7, 17), location=self.bh, mode="in-person")
        AttendanceSessionMember.objects.create(session=s, newcomer=n)
        self.assertEqual(readiness(n, today=D(2026, 10, 16))["first_came"], D(2026, 7, 17))

    def test_whole_months(self):
        self.assertEqual(_months_between(D(2026, 7, 1), D(2027, 1, 1)), 6)
        self.assertEqual(_months_between(D(2026, 7, 31), D(2027, 1, 1)), 5)
        self.assertEqual(_months_between(D(2026, 7, 31), D(2027, 1, 31)), 6)


class RegisteredOnTheDay(Base):
    def test_manual_entry_on_the_day_checks_them_in_to_the_meeting_named(self):
        fri, mon = self.session(), self.session(mt=self.mon)
        r = self.client.post("/api/newcomers/", {"name": "Abel", "source": self.src.id, "location": "bahrain",
                                                 "meeting_attended": "fri-worship", "phone": "+97333000000"}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(list(AttendanceSessionMember.objects.filter(newcomer_id=r.data["id"]).values_list("session_id", flat=True)), [fri.id])

    def test_qr_registration_on_the_day_checks_them_in(self):
        s = self.session()
        Fellowship.objects.create(name="HCF Men", meeting_type=self.house, location=self.bh)
        self.session(mt=self.house, fellowship=Fellowship.objects.get())      # fellowships are not a guess
        self.client.force_authenticate(None)
        r = self.client.post("/api/public/newcomer-registration/?location=bahrain",
                             {"name": "Bunmi", "phone": "+97333111111"}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        n = Newcomer.objects.get(name="Bunmi")
        self.assertEqual(list(n.attendances.values_list("session_id", flat=True)), [s.id])

    def test_nothing_is_guessed(self):
        self.session(); self.session(mt=self.mon)       # two services today, none named
        self.client.post("/api/newcomers/", {"name": "Unclear", "source": self.src.id, "location": "bahrain", "phone": "+97333222222"}, format="json")
        self.assertFalse(AttendanceSessionMember.objects.filter(newcomer__name="Unclear").exists())
        self.client.post("/api/newcomers/", {"name": "Other place", "source": self.src.id, "location": "others",
                                             "meeting_attended": "fri-worship", "phone": "+97333333333"}, format="json")
        self.assertFalse(AttendanceSessionMember.objects.filter(newcomer__name="Other place").exists())
