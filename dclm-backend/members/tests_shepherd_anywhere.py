"""All-locations shepherds anywhere, and who is not offered (5 November 2026)."""
import datetime

from rest_framework.test import APITestCase

from accounts.models import Role, RolePermission, User
from core.models import FollowUpRules, Location
from members.assignment import eligible_shepherds, not_offered
from members.models import Member


class Anywhere(APITestCase):
    def setUp(self):
        self.bh = Location.objects.create(id="bahrain", name="Bahrain HQ", is_core=True)
        self.qa = Location.objects.create(id="others", name="Qatar")
        role = Role.objects.create(name="Administrator")
        RolePermission.objects.create(role=role, module="members", can_view=True, can_edit=True)
        d = datetime.date(2026, 1, 1)
        mk = lambda e, **kw: User.objects.create_user(email=e, password="x", role=role, gender="Male", **kw)
        self.ahmed = mk("ahmed@t.com", first_name="Ahmed", can_shepherd=True,
                        member=Member.objects.create(surname="A", first_name="Ahmed", location=self.qa, joined_date=d))
        self.henry = mk("henry@t.com", first_name="Henry", can_shepherd=True, location=self.qa)
        self.samuel = mk("samuel@t.com", first_name="Samuel", can_shepherd=True, location=self.bh)
        self.paul = mk("paul@t.com", first_name="Paul")
        self.client.force_authenticate(self.samuel)

    def ids(self, loc):
        return {u.id for u in eligible_shepherds(loc)}

    def test_switch_on_all_locations_account_shepherds_anywhere(self):
        self.assertTrue(FollowUpRules.get().shepherd_anywhere)
        self.assertEqual(self.ids("bahrain"), {self.ahmed.id, self.samuel.id})
        self.assertEqual(self.ids("others"), {self.ahmed.id, self.henry.id})

    def test_switch_off_only_at_member_record_location(self):
        r = FollowUpRules.get(); r.shepherd_anywhere = False; r.save()
        self.assertEqual(self.ids("bahrain"), {self.samuel.id})
        why = {x["id"]: x["reason"] for x in not_offered("bahrain")}
        self.assertIn("member record is at Qatar", why[self.ahmed.id])
        self.assertIn("Admin, Follow-up Rules", why[self.ahmed.id])

    def test_reasons_for_those_not_offered(self):
        r = self.client.get("/api/members/shepherds-not-offered/", {"location": "bahrain"})
        self.assertEqual(r.status_code, 200)
        why = {x["id"]: x["reason"] for x in r.data}
        self.assertEqual(why[self.henry.id], "their account covers Qatar only.")
        self.assertIn("Can shepherd others is not ticked", why[self.paul.id])
        self.assertNotIn(self.ahmed.id, why)
        self.assertNotIn(self.samuel.id, why)

    def test_switch_can_be_saved(self):
        admin = User.objects.create_superuser(email="root@t.com", password="x")
        self.client.force_authenticate(admin)
        r = self.client.patch("/api/followup-rules/", {"shepherd_anywhere": False}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertFalse(FollowUpRules.get().shepherd_anywhere)
