"""
Fix first items from the app review (25 October 2026) built with the
follow-up plan: O1 and O2 (a session's saved figures and offering are kept),
P5 (people who said no are never started), P4 (what deleting removes).
"""
import datetime

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Role, RolePermission, User
from attendance.models import AttendanceSession, MeetingType
from core.models import Location
from finance.models import Fund, Giving, PaymentMethod
from members.models import Member


class SessionOfferingTests(APITestCase):
    def setUp(self):
        self.bh = Location.objects.get_or_create(id="bahrain", defaults={"name": "Bahrain HQ", "is_core": True})[0]
        self.fri = MeetingType.objects.create(id="fri", name="Friday Worship Service", day="Friday", frequency="weekly",
                                              detail_level="simple", collects_offering=True)
        Fund.objects.get_or_create(name="Tithe")
        PaymentMethod.objects.get_or_create(name="Cash")
        role = Role.objects.get_or_create(name="Administrator")[0]
        for m in ("attendance", "finance"):
            RolePermission.objects.update_or_create(role=role, module=m, defaults=dict(can_view=True, can_create=True,
                                                                                        can_edit=True, can_delete=True))
        self.client.force_authenticate(User.objects.create_user(email="a@t.com", password="x", role=role))
        self.s = AttendanceSession.objects.create(meeting_type=self.fri, date=timezone.localdate() - datetime.timedelta(days=1),
                                                  location=self.bh, mode="in-person")

    def record(self, **extra):
        body = dict(men=10, women=12, new_comers=3, new_converts=1, **extra)
        return self.client.post(f"/api/attendance-sessions/{self.s.id}/record/", body, format="json")

    def test_saved_figures_come_back_and_offering_is_kept(self):
        self.assertEqual(self.record(offering={"Tithe": "45.000"}).status_code, 200)
        data = self.client.get(f"/api/attendance-sessions/{self.s.id}/").data
        self.assertEqual((data["new_comers"], data["new_converts"], data["offering"]), (3, 1, {"Tithe": "45.000"}))
        g = Giving.objects.get(session=self.s)
        # O2: corrected on Finance is refused, and saving headcounts keeps it.
        r = self.client.patch(f"/api/giving/{g.id}/", {"amount": "50.000"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("Open that session in Attendance", r.data["detail"])
        self.assertEqual(self.record().status_code, 200)
        self.assertTrue(Giving.objects.filter(pk=g.pk).exists())
        self.assertEqual(self.client.get("/api/giving/").data["results"][0]["session_label"][:22], "Friday Worship Service")


class SaidNoTests(APITestCase):
    def test_said_no_listed_apart_and_never_started(self):
        from newcomers.models import Newcomer, NewcomerSource
        bh = Location.objects.get_or_create(id="bahrain", defaults={"name": "Bahrain HQ", "is_core": True})[0]
        src = NewcomerSource.objects.get_or_create(name="Walk-in")[0]
        now, today = timezone.now(), timezone.localdate()
        yes = Newcomer.objects.create(name="Yes Person", source=src, location=bh, created_at=now, stage_since=today)
        no = Newcomer.objects.create(name="No Person", source=src, location=bh, created_at=now, stage_since=today,
                                     keep_in_touch=False)
        from followup.models import Enrolment
        Enrolment.objects.all().delete()
        role = Role.objects.get_or_create(name="Follow-up")[0]
        RolePermission.objects.update_or_create(role=role, module="newcomers", defaults=dict(can_view=True, can_edit=True))
        self.client.force_authenticate(User.objects.create_user(email="f@t.com", password="x", role=role))
        d = self.client.get("/api/followup/start-many/").data
        self.assertEqual(([r["name"] for r in d["results"]], [r["name"] for r in d["said_no"]]), (["Yes Person"], ["No Person"]))
        r = self.client.post("/api/followup/start/", {"journey": "newcomers", "newcomer": no.id}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("unticked Keep in touch", r.data["detail"])


class DeletePreviewTests(APITestCase):
    def test_counts(self):
        bh = Location.objects.get_or_create(id="bahrain", defaults={"name": "Bahrain HQ", "is_core": True})[0]
        role = Role.objects.get_or_create(name="Administrator")[0]
        RolePermission.objects.update_or_create(role=role, module="members", defaults=dict(can_view=True, can_delete=True))
        self.client.force_authenticate(User.objects.create_user(email="a@t.com", password="x", role=role))
        m = Member.objects.create(first_name="Joshua", surname="Afari", location=bh, joined_date=datetime.date(2026, 1, 1))
        r = self.client.get(f"/api/members/{m.id}/delete-preview/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["check_ins"], 0)


class HelpFilesTests(APITestCase):
    """Help & Guide files are for signed-in people only."""

    def test_manual_pictures_and_contacts(self):
        self.assertEqual(self.client.get("/api/help/manual/").status_code, 401)
        u = User.objects.create_user(email="h@t.com", password="x")
        self.client.force_authenticate(u)
        r = self.client.get("/api/help/manual/")
        self.assertEqual((r.status_code, r["Content-Type"]), (200, "application/pdf"))
        self.assertEqual(self.client.get("/api/help/img/reasons/").status_code, 200)
        self.assertEqual(self.client.get("/api/help/img/..%2Fmanual/").status_code, 404)
        self.assertEqual(self.client.get("/api/help/img/nothing/").status_code, 404)
        self.assertIn("administrators", self.client.get("/api/help/contacts/").data)


class DuplicatePhoneTests(APITestCase):
    """Help 11.14: a phone number already on the roll names who has it."""

    def test_names_the_member(self):
        import datetime
        from members.models import Member
        from members.serializers import MemberSerializer
        m = Member.objects.create(first_name="Grace", surname="Okon", gender="Female", phone="+97333334444",
                                  joined_date=datetime.date(2025, 1, 1),
                                  location=Location.objects.get_or_create(id="bahrain", defaults={"name": "Bahrain HQ", "is_core": True})[0])
        s = MemberSerializer(data={"first_name": "A", "surname": "B", "gender": "Female", "phone": "+97333334444",
                                   "location": "bahrain", "joined_date": "2025-01-01"})
        self.assertFalse(s.is_valid())
        self.assertIn("already has this phone number", str(s.errors["phone"]))
        self.assertIn(m.full_name, str(s.errors["phone"]))
        self.assertTrue(MemberSerializer(m, data={"phone": "+97333334444"}, partial=True).is_valid())
