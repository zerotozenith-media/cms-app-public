"""Wrong-day check and Change date or meeting (5 November 2026)."""
import datetime
from decimal import Decimal

from rest_framework.test import APITestCase

from accounts.models import AuditLog, Role, RolePermission, User
from attendance.models import AttendanceSession, MeetingType
from core.models import Location

D = datetime.date


class Base(APITestCase):
    def setUp(self):
        self.bh = Location.objects.create(id="bahrain", name="Bahrain HQ", is_core=True)
        admin = Role.objects.create(name="Administrator")
        for mod in ("attendance", "admin", "finance"):
            RolePermission.objects.create(role=admin, module=mod, can_view=True, can_create=True, can_edit=True, can_delete=True)
        self.admin = User.objects.create_user(email="a@t.com", password="x", role=admin)
        usher = Role.objects.create(name="Usher")
        RolePermission.objects.create(role=usher, module="attendance", can_view=True, can_create=True, can_edit=True)
        self.usher = User.objects.create_user(email="u@t.com", password="x", role=usher)
        self.mon = MeetingType.objects.create(id="mon-bs", name="Monday Bible Study", day="Monday", frequency="weekly", detail_level="detailed")
        self.wed = MeetingType.objects.create(id="wed-rev", name="Wednesday Revival and Evangelism Training", day="Wednesday",
                                              frequency="weekly", detail_level="detailed")
        self.gck = MeetingType.objects.create(id="gck", name="Global Crusade with Kumuyi (GCK)", frequency="occasional", detail_level="detailed")
        self.client.force_authenticate(self.admin)


class WrongDay(Base):
    def add(self, mt, d, **extra):
        return self.client.post("/api/attendance-sessions/", {"meeting_type": mt.id, "date": str(d), "location": "bahrain",
                                                              "mode": "in-person", **extra}, format="json")

    def test_weekly_meeting_on_another_day_asks_first(self):
        r = self.add(self.mon, D(2026, 10, 14))
        self.assertEqual(r.status_code, 400)
        self.assertIn("Monday Bible Study meets on Mondays. 14 October is a Wednesday.", str(r.data["detail"]))
        self.assertTrue(r.data["other_day"])
        self.assertEqual(self.add(self.mon, D(2026, 10, 14), allow_other_day=True).status_code, 201)

    def test_right_day_and_occasional_meetings_are_not_asked(self):
        self.assertEqual(self.add(self.mon, D(2026, 10, 12)).status_code, 201)
        self.assertEqual(self.add(self.gck, D(2026, 10, 14)).status_code, 201)


class Change(Base):
    def setUp(self):
        super().setUp()
        self.s = AttendanceSession.objects.create(meeting_type=self.mon, date=D(2026, 10, 14), location=self.bh,
                                                  mode="in-person", men=5, women=3, status="filled")

    def change(self, **body):
        return self.client.post(f"/api/attendance-sessions/{self.s.id}/change/", body, format="json")

    def test_meeting_changed_keeping_the_numbers_and_offering(self):
        from finance.models import Fund, Giving, PaymentMethod
        g = Giving.objects.create(date=D(2026, 10, 14), fund=Fund.objects.create(name="Offering"),
                                  method=PaymentMethod.objects.create(name="Cash"), amount=Decimal("4.000"),
                                  location=self.bh, session=self.s)
        r = self.change(meeting_type=self.wed.id)
        self.assertEqual(r.status_code, 200, r.data)
        self.s.refresh_from_db(); g.refresh_from_db()
        self.assertEqual((self.s.meeting_type_id, self.s.total, g.session_id), ("wed-rev", 8, self.s.id))
        log = AuditLog.objects.filter(action="Changed").latest("id")
        self.assertIn("Was Monday Bible Study, Wed 14 Oct 2026. Now Wednesday Revival and Evangelism Training", log.details)

    def test_date_moves_the_offering_too(self):
        from finance.models import Fund, Giving, PaymentMethod
        g = Giving.objects.create(date=D(2026, 10, 14), fund=Fund.objects.create(name="Offering"),
                                  method=PaymentMethod.objects.create(name="Cash"), amount=Decimal("4.000"),
                                  location=self.bh, session=self.s)
        self.assertEqual(self.change(date="2026-10-12").status_code, 200)
        g.refresh_from_db()
        self.assertEqual(g.date, D(2026, 10, 12))

    def test_refusals_explain_themselves(self):
        self.assertIn("Nothing changed", str(self.change(meeting_type=self.mon.id, date="2026-10-14").data))
        r = self.change(date="2026-10-13")
        self.assertIn("meets on Mondays", str(r.data))
        twin = AttendanceSession.objects.create(meeting_type=self.wed, date=D(2026, 10, 14), location=self.bh, mode="in-person")
        r = self.change(meeting_type=self.wed.id)
        self.assertEqual((r.status_code, r.data["existing_id"]), (400, twin.id))
        self.assertIn("already exists", str(r.data))
        r = self.change(date=str(datetime.date.today() + datetime.timedelta(days=7)), allow_other_day=True)
        self.assertIn("has not come yet", str(r.data))

    def test_open_follow_up_tasks_block_the_change(self):
        from members.models import Member, MemberFollowUpTask
        m = Member.objects.create(surname="A", first_name="B", location=self.bh, joined_date=D(2026, 1, 1))
        MemberFollowUpTask.objects.create(member=m, missed_session=self.s, due_date=D(2026, 10, 15))
        r = self.change(date="2026-10-12")
        self.assertIn("open follow-up task was made", str(r.data))

    def test_only_administrators(self):
        self.client.force_authenticate(self.usher)
        self.assertEqual(self.change(date="2026-10-12").status_code, 403)


class FellowshipDelete(Base):
    def setUp(self):
        super().setUp()
        from attendance.models import Fellowship
        self.hcf = MeetingType.objects.create(id="fri-house", name="Friday House Caring Fellowship", day="Friday",
                                              frequency="weekly", detail_level="detailed")
        self.fel = Fellowship.objects.create(name="Women / Sisters Meeting", meeting_type=self.hcf, location=self.bh)
        self.empty = [AttendanceSession.objects.create(meeting_type=self.hcf, fellowship=self.fel, date=d, location=self.bh,
                                                       mode="in-person") for d in (D(2026, 10, 2), D(2026, 10, 9))]

    def test_empty_sessions_go_with_it(self):
        r = self.client.delete(f"/api/fellowships/{self.fel.id}/")
        self.assertEqual(r.status_code, 204, getattr(r, "data", None))
        self.assertFalse(AttendanceSession.objects.filter(pk__in=[s.pk for s in self.empty]).exists())
        self.assertIn("2 empty sessions removed", AuditLog.objects.filter(entity_type="Fellowship").latest("id").details)

    def test_sessions_with_records_are_listed_to_move(self):
        AttendanceSession.objects.create(meeting_type=self.hcf, fellowship=self.fel, date=D(2026, 10, 16), location=self.bh,
                                         mode="in-person", women=9, status="filled")
        r = self.client.delete(f"/api/fellowships/{self.fel.id}/")
        self.assertEqual(r.status_code, 400)
        self.assertIn("1 session with attendance", str(r.data))
        self.assertIn("16 Oct 2026", str(r.data))
        self.assertIn("Change date or meeting", str(r.data))
        self.assertEqual(AttendanceSession.objects.filter(fellowship=self.fel).count(), 3)
