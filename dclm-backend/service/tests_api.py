"""F21: who sees what on the service ladder."""
import datetime

from accounts.models import Role, RolePermission, User
from core.tests_upgrade import Base
from newcomers.models import NewcomerTask

from .models import ServiceStanding

D = datetime.timedelta


class ServiceApiTestCase(Base):
    def setUp(self):
        super().setUp()
        role = Role.objects.create(name="Shepherd test")
        RolePermission.objects.create(role=role, module="newcomers", can_view=True, can_edit=True, can_create=True)
        self.bah = User.objects.create_user(email="b@t.com", password="x", role=role, location=self.bahrain, can_shepherd=True, first_name="Ada", last_name="Bahrain")
        self.qat = User.objects.create_user(email="q@t.com", password="x", role=role, location=self.others, can_shepherd=True, first_name="Zed", last_name="Qatar")
        fin = Role.objects.create(name="Finance test")
        RolePermission.objects.create(role=fin, module="finance", can_view=True)
        self.fin = User.objects.create_user(email="f@t.com", password="x", role=fin, location=self.bahrain, first_name="Fay", last_name="Finance")
        n = self.newcomer("Followed", stage="attending"); n.assigned_to = self.bah; n.save()
        for _ in range(26):
            NewcomerTask.objects.create(newcomer=n, text="Visit", due_date=self.today, assigned_to=self.bah, done=True, contact_date=self.today)

    def as_(self, u):
        self.client.force_authenticate(user=u)

    def test_my_standing_with_next_steps(self):
        self.as_(self.bah)
        d = self.client.get("/api/service/me/").data
        self.assertEqual((d["level_name"], d["points"], d["next_level_name"], d["points_needed"]), ("Labourer", 260, "Soul Winner", 190))
        self.assertTrue(d["steps"] and d["note"] is None)

    def test_someone_who_follows_nobody_up_has_no_standing(self):
        self.as_(self.fin)
        self.assertEqual(self.client.get("/api/service/me/").data, {"eligible": False})

    def test_the_team_is_their_location_by_level_then_name_with_points(self):
        self.as_(self.fin)
        rows = self.client.get("/api/service/team/").data["results"]
        names = [r["name"] for r in rows]
        self.assertIn("Ada Bahrain", names); self.assertNotIn("Zed Qatar", names); self.assertNotIn("Fay Finance", names)
        self.assertEqual(rows[0]["name"], "Ada Bahrain"); self.assertEqual(rows[0]["points"], 260)
        self.assertEqual([r["level"] for r in rows], sorted([r["level"] for r in rows], reverse=True))

    def test_a_moved_up_note_shows_once_and_can_be_dismissed(self):
        ServiceStanding.objects.create(user=self.bah, level=0, since=self.today - D(days=30))
        self.as_(self.bah)
        d = self.client.get("/api/service/me/").data
        self.assertEqual(d["note"]["kind"], "moved_up")
        self.client.post("/api/service/me/dismiss/", {}, format="json")
        self.assertIsNone(self.client.get("/api/service/me/").data["note"])

    def test_during_a_notice_the_steps_are_to_keep_the_level(self):
        ServiceStanding.objects.create(user=self.bah, level=3, since=self.today - D(days=60))
        self.as_(self.bah)
        d = self.client.get("/api/service/me/").data
        self.assertEqual((d["level_name"], d["keeping"], d["note"]["kind"], d["points_needed"]), ("Soul Winner", True, "notice", 190))
        self.assertIn("30 days to keep Soul Winner", d["note"]["text"])

    def test_signed_out_is_refused(self):
        self.client.logout()
        self.assertEqual(self.client.get("/api/service/team/").status_code, 401)
        self.assertEqual(self.client.get("/api/service/me/").status_code, 401)
