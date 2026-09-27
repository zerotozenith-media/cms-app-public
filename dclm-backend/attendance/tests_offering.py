"""
The offering on a session: recorded once, as giving linked to that
meeting, and only when the meeting is marked as collecting one.
"""
import datetime
from decimal import Decimal

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Role, RolePermission, User
from attendance.models import AttendanceSession, MeetingType
from core.models import Location
from finance.models import Fund, Giving


class OfferingOnSessionTestCase(APITestCase):
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        role = Role.objects.create(name="Administrator")
        for m in ["members", "attendance", "newcomers", "finance",
                  "goals", "reports", "outreach", "admin"]:
            RolePermission.objects.create(role=role, module=m, can_view=True,
                                          can_create=True, can_edit=True, can_delete=True)
        self.admin = User.objects.create_user(email="a@t.com", password="x", role=role)
        self.client.force_authenticate(user=self.admin)
        self.tithe = Fund.objects.create(name="Tithe")
        self.offering_fund = Fund.objects.create(name="Offering")
        self.today = timezone.localdate()

        self.collecting = MeetingType.objects.create(
            id="fri-worship", name="Friday Worship", day="Friday",
            frequency="weekly", detail_level="detailed", collects_offering=True)
        self.not_collecting = MeetingType.objects.create(
            id="gck", name="Global Crusade", day="", frequency="occasional",
            detail_level="detailed", collects_offering=False)

    def session(self, mt):
        return AttendanceSession.objects.create(
            meeting_type=mt, date=self.today, location=self.bahrain,
            mode="in-person", status="pending")

    def record(self, s, offering):
        return self.client.post(f"/api/attendance-sessions/{s.id}/record/",
                                {"men": 20, "women": 25, "offering": offering},
                                format="json")

    def test_an_offering_is_saved_as_giving_linked_to_the_session(self):
        s = self.session(self.collecting)
        resp = self.record(s, {"Tithe": "120.500", "Offering": "40.000"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(s.giving.count(), 2)
        self.assertEqual(sum(g.amount for g in s.giving.all()), Decimal("160.500"))

    def test_it_appears_under_giving_and_finance(self):
        """One record, visible in both places, rather than two that can
        disagree."""
        s = self.session(self.collecting)
        self.record(s, {"Tithe": "100.000"})
        self.assertEqual(Giving.objects.filter(session=s).count(), 1)
        self.assertEqual(Giving.objects.count(), 1)

    def test_a_meeting_that_does_not_collect_records_nothing(self):
        s = self.session(self.not_collecting)
        self.record(s, {"Tithe": "100.000"})
        self.assertEqual(s.giving.count(), 0)

    def test_saving_again_replaces_rather_than_adds(self):
        """Otherwise correcting a figure would double the money."""
        s = self.session(self.collecting)
        self.record(s, {"Tithe": "100.000"})
        self.record(s, {"Tithe": "150.000"})
        self.assertEqual(s.giving.count(), 1)
        self.assertEqual(s.giving.first().amount, Decimal("150.000"))

    def test_lowering_an_amount_to_zero_removes_it(self):
        s = self.session(self.collecting)
        self.record(s, {"Tithe": "100.000", "Offering": "50.000"})
        self.record(s, {"Tithe": "100.000", "Offering": "0"})
        self.assertEqual(s.giving.count(), 1)

    def test_an_unknown_fund_is_ignored_rather_than_crashing(self):
        s = self.session(self.collecting)
        resp = self.record(s, {"Tithe": "100.000", "NoSuchFund": "50.000"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(s.giving.count(), 1)

    def test_the_giving_is_dated_to_the_meeting(self):
        """Not to the day somebody happened to type it in."""
        s = AttendanceSession.objects.create(
            meeting_type=self.collecting,
            date=self.today - datetime.timedelta(days=3),
            location=self.bahrain, mode="in-person", status="pending")
        self.record(s, {"Tithe": "100.000"})
        self.assertEqual(s.giving.first().date, s.date)

    def test_recording_no_offering_is_fine(self):
        s = self.session(self.collecting)
        resp = self.client.post(f"/api/attendance-sessions/{s.id}/record/",
                                {"men": 10, "women": 12}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(s.giving.count(), 0)
